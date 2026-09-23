import { useEffect, useMemo, useState } from "react";
import { IconChevronLeft, IconChevronRight, IconClose, IconSparkle } from "../components/icons.tsx";
import { fetchStoryVideoUrl, getStudentStory, type StoryScript, type StudentStory } from "../studentAiApi.ts";

interface Frame {
  kind: "intro" | "scene" | "outro";
  caption: string;
  visual: string;
  narration: string;
  seconds: number;
}

function buildFrames(script: StoryScript): Frame[] {
  return [
    { kind: "intro", caption: script.title, visual: "", narration: script.hook, seconds: 5 },
    ...script.scenes.map((s) => ({
      kind: "scene" as const,
      caption: s.on_screen_text,
      visual: s.visual,
      narration: s.narration,
      seconds: s.seconds,
    })),
    { kind: "outro", caption: "Remember", visual: "", narration: script.takeaway, seconds: 6 },
  ];
}

const speechSupported = typeof window !== "undefined" && "speechSynthesis" in window;

interface StoryPlayerProps {
  title: string;
  script: StoryScript;
  narratorName: string | null;
  /** "storyboard" plays the script scene by scene; "video" plays a rendered file. */
  kind: "storyboard" | "video";
  videoUrl?: string | null;
  onClose: () => void;
}

/**
 * A story-style player: one tall card, a progress segment per scene, captions
 * and the narrator's line. In storyboard mode (no video provider connected)
 * the scenes are described rather than filmed, and the narration can be read
 * aloud by the browser -- the card says so plainly.
 */
export default function StoryPlayer({ title, script, narratorName, kind, videoUrl, onClose }: StoryPlayerProps) {
  const frames = useMemo(() => buildFrames(script), [script]);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [sound, setSound] = useState(false);
  const frame = frames[index];
  const showVideo = kind === "video" && !!videoUrl;

  // Advance when the scene's time is up and, with narration on, the line has been spoken.
  useEffect(() => {
    if (showVideo || !playing) return;
    let cancelled = false;
    let timerDone = false;
    let speechDone = !(sound && speechSupported);

    const advance = () => {
      if (cancelled || !timerDone || !speechDone) return;
      if (index + 1 < frames.length) setIndex(index + 1);
      else setPlaying(false);
    };

    if (sound && speechSupported) {
      const utterance = new SpeechSynthesisUtterance(frame.narration);
      utterance.onend = utterance.onerror = () => {
        speechDone = true;
        advance();
      };
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
    }
    const timer = window.setTimeout(() => {
      timerDone = true;
      advance();
    }, frame.seconds * 1000);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      if (sound && speechSupported) window.speechSynthesis.cancel();
    };
  }, [index, playing, sound, frame, frames.length, showVideo]);

  useEffect(() => () => void (speechSupported && window.speechSynthesis.cancel()), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") setIndex((i) => Math.min(i + 1, frames.length - 1));
      else if (e.key === "ArrowLeft") setIndex((i) => Math.max(i - 1, 0));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [frames.length, onClose]);

  const narrator = narratorName ?? "Your instructor";
  const finished = !playing && index === frames.length - 1;

  return (
    <div className="modal-backdrop story-backdrop" onClick={onClose}>
      <div className="story-card" role="dialog" aria-label={`Story: ${title}`} onClick={(e) => e.stopPropagation()}>
        {!showVideo && (
          <div className="story-progress" aria-hidden="true">
            {frames.map((f, i) => (
              <span className="story-seg" key={i}>
                {i < index && <span className="story-seg-fill is-done" />}
                {i === index && (
                  <span
                    key={`${index}-${playing}`}
                    className="story-seg-fill is-current"
                    style={{ animationDuration: `${f.seconds}s`, animationPlayState: playing ? "running" : "paused" }}
                  />
                )}
              </span>
            ))}
          </div>
        )}

        <div className="story-head">
          <span className="story-avatar" aria-hidden="true">{narrator.charAt(0).toUpperCase()}</span>
          <div className="story-head-text">
            <strong>{narrator}</strong>
            <span>{title}</span>
          </div>
          <span className={`status-pill ${kind === "video" ? "status-published" : "status-draft"}`}>
            {kind === "video" ? "Video" : "Storyboard"}
          </span>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close story">
            <IconClose />
          </button>
        </div>

        {showVideo ? (
          <video className="story-video" src={videoUrl!} controls autoPlay playsInline />
        ) : (
          <>
            <div className={`story-stage story-stage--${frame.kind}`} aria-live="polite">
              {frame.kind === "scene" && frame.visual && (
                <p className="story-visual"><IconSparkle /> {frame.visual}</p>
              )}
              <p className="story-caption">{frame.caption}</p>
            </div>
            <p className="story-narration">{frame.narration}</p>

            <div className="story-controls">
              <button type="button" className="btn" onClick={() => setIndex(Math.max(index - 1, 0))} disabled={index === 0} aria-label="Previous scene">
                <IconChevronLeft />
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  if (finished) {
                    setIndex(0);
                    setPlaying(true);
                  } else setPlaying(!playing);
                }}
              >
                {finished ? "Watch again" : playing ? "Pause" : "Play"}
              </button>
              <button type="button" className="btn" onClick={() => setIndex(Math.min(index + 1, frames.length - 1))} disabled={index === frames.length - 1} aria-label="Next scene">
                <IconChevronRight />
              </button>
              {speechSupported && (
                <button type="button" className={`btn${sound ? " is-active" : ""}`} aria-pressed={sound} onClick={() => setSound(!sound)}>
                  Narration {sound ? "on" : "off"}
                </button>
              )}
            </div>
            <p className="hint story-note">
              A storyboard: the scenes are described rather than filmed, because no video provider is connected yet.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

/** Loads a ready story for a student (and its video file, if it has one) and plays it. */
export function StudentStoryViewer({ courseId, moduleId, onClose }: { courseId: string; moduleId: string; onClose: () => void }) {
  const [story, setStory] = useState<StudentStory | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    (async () => {
      try {
        const s = await getStudentStory(courseId, moduleId);
        if (cancelled) return;
        setStory(s);
        if (s.kind === "video") {
          objectUrl = await fetchStoryVideoUrl(courseId, moduleId);
          if (!cancelled) setVideoUrl(objectUrl);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "This story couldn't be loaded.");
      }
    })();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [courseId, moduleId]);

  if (error) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal-card" onClick={(e) => e.stopPropagation()}>
          <div className="error-banner">{error}</div>
          <button type="button" className="btn" onClick={onClose}>Close</button>
        </div>
      </div>
    );
  }
  if (!story) return null;
  return (
    <StoryPlayer
      title={story.title}
      script={story.script}
      narratorName={story.narrator.name}
      kind={story.kind}
      videoUrl={videoUrl}
      onClose={onClose}
    />
  );
}
