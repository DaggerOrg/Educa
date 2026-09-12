import "@copilotkit/react-ui/v2/styles.css";
import { HttpAgent } from "@ag-ui/client";
import { CopilotChat, CopilotKitProvider, useAgentContext, useConfigureSuggestions } from "@copilotkit/react-core/v2";
import type { JsonSerializable } from "@copilotkit/react-core/v2";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import {
  ApiError,
  browseListings,
  deactivateListing,
  fetchCourse,
  listMyCourses,
  listMyListings,
  publishLesson,
  setApproval,
} from "./api.ts";
import { getSession, logOut, type Session } from "./auth.ts";
import AccountMenu from "./components/AccountMenu.tsx";
import AccountModal, { type AccountModalKind } from "./components/AccountModal.tsx";
import { useCurriculumApprovals } from "./components/ApprovalCards.tsx";
import Auth from "./components/Auth.tsx";
import CourseToolsRail, { type CourseTool } from "./components/CourseToolsRail.tsx";
import ExercisesBuilder from "./components/ExercisesBuilder.tsx";
import RoutinePanel from "./components/RoutinePanel.tsx";
import SettingsPanel from "./components/SettingsPanel.tsx";
import ThemeToggle from "./components/ThemeToggle.tsx";
import {
  IconChat,
  IconChevronLeft,
  IconClose,
  IconCourse,
  IconEdit,
  IconGraph,
  IconSettings,
  IconSparkle,
  IconStore,
  IconTag,
} from "./components/icons.tsx";
import KnowledgeGraphSection from "./knowledge-graph/KnowledgeGraphSection.tsx";
import Home from "./components/Home.tsx";
import LessonPanel from "./components/LessonPanel.tsx";
import ListingForm from "./components/ListingForm.tsx";
import Marketplace from "./components/Marketplace.tsx";
import SyllabusView from "./components/SyllabusView.tsx";
import TeacherChat from "./components/TeacherChat.tsx";
import WelcomePanel from "./components/WelcomePanel.tsx";
import { STARTER_SUGGESTIONS } from "./starterSuggestions.ts";
import EducaApp from "./educa/EducaApp.tsx";
import { formatPrice } from "./format.ts";
import type { Course, Lesson, Listing, Week } from "./types.ts";

const AGUI_URL = import.meta.env.VITE_AGUI_URL || "http://localhost:8000/agui";

export default function App() {
  const [session, setSession] = useState<Session | null>(() => getSession());

  if (!session) {
    return <Auth onAuthenticated={setSession} />;
  }

  const handleLogOut = () => {
    logOut();
    setSession(null);
  };

  return (
    <Routes>
      {/* The traditional, Moodle-style platform: catalog, enrollment,
          reading a published lesson, taking its quiz -- usable by either
          role. Studio (below) is the AI course-authoring tool, teacher-only. */}
      <Route path="/educa/*" element={<EducaApp session={session} onLogOut={handleLogOut} />} />
      <Route
        path="/*"
        element={
          session.user.role === "teacher" ? (
            <AuthenticatedApp session={session} onLogOut={handleLogOut} />
          ) : (
            // Studio's chat and course routes are teacher-only server-side
            // (backend/app/main.py's require_role("teacher")) -- a student
            // account has nothing to do here.
            <Navigate to="/educa" replace />
          )
        }
      />
    </Routes>
  );
}

interface AuthenticatedAppProps {
  session: Session;
  onLogOut: () => void;
}

function AuthenticatedApp({ session, onLogOut }: AuthenticatedAppProps) {
  // `agents__unsafe_dev_only` points CopilotKit straight at Agno's AG-UI
  // endpoint, bypassing the "CopilotRuntime" that @copilotkit/react-core
  // normally expects at `runtimeUrl`. It's the documented escape hatch for
  // exactly this case (no Node runtime in front of the agent) -- but
  // CopilotKit's own types label it dev-only, and a real deployment should
  // either get a first-party Agno adapter or run a thin runtime in front.
  // See the README for the alternative (LangGraph + copilotkit's Python
  // SDK) this replaced, and why.
  const agent = useMemo(
    () => new HttpAgent({ url: AGUI_URL, headers: { Authorization: `Bearer ${session.token}` } }),
    [session.token],
  );

  return (
    <CopilotKitProvider agents__unsafe_dev_only={{ curriculum_team: agent }}>
      <Studio session={session} onLogOut={onLogOut} />
    </CopilotKitProvider>
  );
}

function Studio({ session, onLogOut }: AuthenticatedAppProps) {
  const [myCourses, setMyCourses] = useState<Course[]>([]);
  const [courseId, setCourseId] = useState<string | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [selectedLessonId, setSelectedLessonId] = useState<string | null>(null);
  const [editedIds, setEditedIds] = useState<Set<string>>(() => new Set());
  const [error, setError] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [section, setSection] = useState<"courses" | "course" | "marketplace" | "knowledge-graph" | "chat" | "settings">("course");
  const [navExpanded, setNavExpanded] = useState(true);
  const [courseTool, setCourseTool] = useState<CourseTool>("syllabus");
  const [materialsModalOpen, setMaterialsModalOpen] = useState(false);
  const [accountModal, setAccountModal] = useState<AccountModalKind | null>(null);
  const [myListings, setMyListings] = useState<Listing[]>([]);
  const [listingCourse, setListingCourse] = useState<Course | null>(null);
  const [marketplaceQuery, setMarketplaceQuery] = useState("");
  const [marketplaceListings, setMarketplaceListings] = useState<Listing[]>([]);
  const [marketplaceLoading, setMarketplaceLoading] = useState(false);
  const [marketplaceError, setMarketplaceError] = useState<string | null>(null);

  // Static starters shown as suggestion pills in the chat before the first
  // message -- gives a first-time teacher something to click instead of
  // facing a blank "type a message" box.
  useConfigureSuggestions({ available: "before-first-message", suggestions: STARTER_SUGGESTIONS }, []);

  // Renders an approve/reject card for each of the four curriculum-agent
  // tools (all `requires_confirmation=True`, see backend/app/agents/*/tools.py)
  // right in the chat, instead of only gating publish at the very end.
  useCurriculumApprovals(course);

  const refreshCourseList = useCallback(async () => {
    try {
      const list = await listMyCourses();
      setMyCourses(list);
      // Auto-select on first load (or right after create_syllabus makes the
      // very first course) -- once a course is open, a second course
      // appearing shouldn't yank the teacher away from what they're editing.
      setCourseId((prev) => prev ?? list[list.length - 1]?.id ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    refreshCourseList();
    const id = setInterval(refreshCourseList, 2000);
    return () => clearInterval(id);
  }, [refreshCourseList]);

  const refreshMyListings = useCallback(async () => {
    try {
      setMyListings(await listMyListings());
    } catch {
      // Non-critical: the "List on Marketplace" control just won't reflect
      // an already-active listing until the next successful poll.
    }
  }, []);

  useEffect(() => {
    refreshMyListings();
    const id = setInterval(refreshMyListings, 5000);
    return () => clearInterval(id);
  }, [refreshMyListings]);

  useEffect(() => {
    if (section !== "marketplace") return;
    let cancelled = false;
    setMarketplaceLoading(true);
    setMarketplaceError(null);
    browseListings(marketplaceQuery || undefined)
      .then((data) => { if (!cancelled) setMarketplaceListings(data); })
      .catch((e) => { if (!cancelled) setMarketplaceError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setMarketplaceLoading(false); });
    return () => { cancelled = true; };
  }, [section, marketplaceQuery]);

  const refresh = useCallback(async () => {
    if (!courseId) {
      setCourse(null);
      return;
    }
    try {
      const data = await fetchCourse(courseId);
      setCourse(data);
      setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) setCourse(null);
      else setError(e instanceof Error ? e.message : String(e));
    }
  }, [courseId]);

  useEffect(() => {
    refresh();
    // Poll rather than hook a chat-completion callback: it's a few lines of
    // extra latency in exchange for not depending on an exact prop name in
    // a React package that's still moving fast (see README).
    const id = setInterval(refresh, 2000);
    return () => clearInterval(id);
  }, [refresh]);

  // Push the current syllabus -- and which lessons the teacher has hand-edited
  // -- into the agent's context on every turn. This is the mechanism behind
  // SRS FR-1.4 / ARCH-01 SS03: a refinement prompt can only preserve a manual
  // edit if the model can actually see which lessons were touched. `course.id`
  // is also how the model knows which course update_syllabus should target
  // once a teacher has more than one.
  useAgentContext({
    description:
      "The current course syllabus, including its id. `edited` lists lesson " +
      "ids the teacher has hand-edited since the last AI change -- preserve " +
      "those lessons' title and objective exactly unless the teacher's " +
      "instruction targets them. If no course is shown, the teacher hasn't " +
      "started one yet -- call create_syllabus to start a new course.",
    value: (course ? { ...course, edited: [...editedIds] } : "No course selected.") as unknown as JsonSerializable,
  });

  function markEdited(lessonId: string) {
    setEditedIds((prev) => new Set(prev).add(lessonId));
  }

  async function handleApprove(lessonId: string, approved: boolean) {
    await setApproval(lessonId, approved);
    refresh();
  }

  async function handlePublish(lessonId: string) {
    await publishLesson(lessonId);
    refresh();
  }

  async function handleUnlist(listing: Listing) {
    await deactivateListing(listing.id);
    refreshMyListings();
  }

  function handleBought(boughtCourse: Course) {
    setCourseId(boughtCourse.id);
    setSelectedLessonId(null);
    setEditedIds(new Set());
    setCourseTool("syllabus");
    setSection("course");
    refreshCourseList();
  }

  const selectedLesson = course ? findLesson(course, selectedLessonId) : null;
  const selectedWeek = course ? findLessonWeek(course, selectedLessonId) : null;
  const activeListing = course ? myListings.find((l) => l.courseId === course.id && l.isActive) : undefined;

  return (
    <div className="layout">
      <header className="topbar">
        <div className="wordmark">EDUCA<span>.</span></div>
        <div className="topbar-right">
          {myCourses.length > 0 && (
            <select
              className="course-switcher"
              value={courseId ?? ""}
              onChange={(e) => {
                setCourseId(e.target.value || null);
                setSelectedLessonId(null);
                setEditedIds(new Set());
                if (!e.target.value) setChatOpen(true);
              }}
            >
              {myCourses.map((c) => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
              <option value="">+ New course</option>
            </select>
          )}
          {section === "course" && course && (
            activeListing ? (
              <button
                type="button"
                className="status-pill status-approved topbar-listed"
                title="Click to unlist"
                onClick={() => handleUnlist(activeListing)}
              >
                <IconTag /> Listed · {formatPrice(activeListing.priceCents)}
              </button>
            ) : (
              <button type="button" className="btn" onClick={() => setListingCourse(course)}>
                <IconTag /> List on Marketplace
              </button>
            )
          )}
          <Link to="/educa" className="btn">Traditional view</Link>
          <button
            type="button"
            className={`btn ask-ai-btn${chatOpen ? " is-active" : ""}`}
            onClick={() => setChatOpen((open) => !open)}
          >
            <IconSparkle /> Ask AI
          </button>
          <div className="topbar-account">
            <ThemeToggle />
            <AccountMenu
              session={session}
              onOpenSettings={() => setSection("settings")}
              onOpenModal={setAccountModal}
              onLogOut={onLogOut}
            />
          </div>
        </div>
      </header>

      <div className="workspace">
        <nav className={`nav-drawer${navExpanded ? "" : " is-collapsed"}`}>
          <div className="nav-drawer-scroll">
          <div className="nav-drawer-items">
            <button
              type="button"
              className={`nav-drawer-btn${section === "courses" ? " is-active" : ""}`}
              title="Home"
              aria-current={section === "courses" ? "page" : undefined}
              onClick={() => setSection("courses")}
            >
              <IconCourse />
              <span className="nav-drawer-label">Home</span>
            </button>
            <button
              type="button"
              className={`nav-drawer-btn${section === "course" ? " is-active" : ""}`}
              title="Course builder"
              aria-current={section === "course" ? "page" : undefined}
              onClick={() => {
                // Always land back on the module list, not whatever lesson
                // page (or tool) was last open -- matches Home/Marketplace/
                // course-switcher, which all reset selectedLessonId when
                // entering a course.
                setSelectedLessonId(null);
                setCourseTool("syllabus");
                setSection("course");
              }}
            >
              <IconEdit />
              <span className="nav-drawer-label">Course builder</span>
            </button>
            <button
              type="button"
              className={`nav-drawer-btn${section === "marketplace" ? " is-active" : ""}`}
              title="Marketplace"
              aria-current={section === "marketplace" ? "page" : undefined}
              onClick={() => setSection("marketplace")}
            >
              <IconStore />
              <span className="nav-drawer-label">Marketplace</span>
            </button>
            <button
              type="button"
              className={`nav-drawer-btn${section === "knowledge-graph" ? " is-active" : ""}`}
              title="Knowledge Graph"
              aria-current={section === "knowledge-graph" ? "page" : undefined}
              onClick={() => setSection("knowledge-graph")}
            >
              <IconGraph />
              <span className="nav-drawer-label">Knowledge Graph</span>
            </button>
            <button
              type="button"
              className={`nav-drawer-btn${section === "chat" ? " is-active" : ""}`}
              title="Chat"
              aria-current={section === "chat" ? "page" : undefined}
              onClick={() => setSection("chat")}
            >
              <IconChat />
              <span className="nav-drawer-label">Chat</span>
            </button>
          </div>

          {/* Settings, and anything else about the platform rather than a
              course, stays pinned at the bottom of the drawer, separate from
              the course-authoring items above. */}
          <div className="nav-drawer-bottom">
            <button
              type="button"
              className={`nav-drawer-btn${section === "settings" ? " is-active" : ""}`}
              title="Settings"
              aria-current={section === "settings" ? "page" : undefined}
              onClick={() => setSection("settings")}
            >
              <IconSettings />
              <span className="nav-drawer-label">Settings</span>
            </button>
          </div>
          </div>
          <button
            type="button"
            className="nav-drawer-toggle"
            title={navExpanded ? "Collapse navigation" : "Expand navigation"}
            aria-label={navExpanded ? "Collapse navigation" : "Expand navigation"}
            onClick={() => setNavExpanded((v) => !v)}
          >
            <IconChevronLeft className="nav-drawer-toggle-icon" />
          </button>
        </nav>

        <div className="workspace-main">
          {error && <div className="error-banner workspace-error">{error}</div>}
          {section === "settings" ? (
            <SettingsPanel session={session} />
          ) : section === "knowledge-graph" ? (
            <KnowledgeGraphSection session={session} />
          ) : section === "chat" ? (
            <TeacherChat session={session} courses={myCourses} />
          ) : section === "courses" ? (
            <Home
              courses={myCourses}
              listings={myListings}
              onOpenCourse={(id) => {
                setCourseId(id);
                setSelectedLessonId(null);
                setEditedIds(new Set());
                setCourseTool("syllabus");
                setSection("course");
              }}
              onNewCourse={() => {
                setCourseId(null);
                setCourse(null);
                setSelectedLessonId(null);
                setEditedIds(new Set());
                setCourseTool("syllabus");
                setSection("course");
                setChatOpen(true);
              }}
              onStartChat={() => {
                // Home's own inline "describe a course" chat stays on Home
                // (see Home.tsx's `chatStarted`) -- this only clears which
                // course the agent context (below) points at, so the first
                // message reads as "no course yet" and triggers
                // create_syllabus instead of update_syllabus.
                setCourseId(null);
                setCourse(null);
                setSelectedLessonId(null);
                setEditedIds(new Set());
              }}
              onListCourse={setListingCourse}
              onUnlist={handleUnlist}
            />
          ) : section === "marketplace" ? (
            <Marketplace
              listings={marketplaceListings}
              loading={marketplaceLoading}
              error={marketplaceError}
              query={marketplaceQuery}
              onQueryChange={setMarketplaceQuery}
              onBought={handleBought}
            />
          ) : !course ? (
            <WelcomePanel onOpenChat={() => setChatOpen(true)} />
          ) : (
            <>
              <CourseToolsRail active={courseTool} onSelect={setCourseTool} />
              {courseTool === "exercises" ? (
                <ExercisesBuilder course={course} selectedLessonId={selectedLessonId} onSelectLesson={setSelectedLessonId} />
              ) : selectedLessonId ? (
                <LessonPanel
                  lesson={selectedLesson}
                  week={selectedWeek}
                  onBack={() => setSelectedLessonId(null)}
                  onEdited={markEdited}
                  onApprove={handleApprove}
                  onPublish={handlePublish}
                  onAddMaterial={() => setMaterialsModalOpen(true)}
                />
              ) : (
                <SyllabusView course={course} onSelect={setSelectedLessonId} />
              )}
            </>
          )}
        </div>
      </div>

      {chatOpen && (
        <>
          <div className="chat-backdrop" onClick={() => setChatOpen(false)} />
          {/* `dark` -- Tailwind ancestor-class convention CopilotKit's own
              v2 stylesheet uses for its dark palette (see
              @copilotkit/react-core/v2/styles.css's `:is(.dark *)`
              utilities); without it CopilotChat renders its light theme
              regardless of Studio's own black palette. */}
          <aside className="chat-drawer dark">
            <div className="chat-drawer-head">
              <span>Ask AI</span>
              <button
                type="button"
                className="chat-drawer-close"
                onClick={() => setChatOpen(false)}
                aria-label="Close Ask AI"
              >
                <IconClose />
              </button>
            </div>
            {/* v2's CopilotChat has no `instructions` prop -- that was a silent
                no-op in the pre-TS JS version. The agent's real instructions
                live server-side in backend/app/agents/curriculum/agent.py. */}
            <CopilotChat agentId="curriculum_team" />
          </aside>
        </>
      )}

      {materialsModalOpen && (
        <div className="modal-backdrop" onClick={() => setMaterialsModalOpen(false)}>
          <div className="modal-card modal-card--wide" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <span>Add material</span>
              <button
                type="button"
                className="modal-close"
                onClick={() => setMaterialsModalOpen(false)}
                aria-label="Close"
              >
                <IconClose />
              </button>
            </div>
            <RoutinePanel />
          </div>
        </div>
      )}

      {listingCourse && (
        <ListingForm
          course={listingCourse}
          onClose={() => setListingCourse(null)}
          onCreated={() => {
            setListingCourse(null);
            refreshMyListings();
          }}
        />
      )}

      {accountModal && <AccountModal kind={accountModal} onClose={() => setAccountModal(null)} />}
    </div>
  );
}

export function findLesson(course: Course, id: string | null | undefined): Lesson | null {
  for (const w of course.weeks) {
    for (const l of w.lessons) {
      if (l.id === id) return l;
    }
  }
  return null;
}

export function findLessonWeek(course: Course, id: string | null | undefined): Week | null {
  for (const w of course.weeks) {
    if (w.lessons.some((l) => l.id === id)) return w;
  }
  return null;
}
