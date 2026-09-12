import { useEffect, useState } from "react";
import { buyListing, fetchListing } from "../api.ts";
import { formatPrice } from "../format.ts";
import type { Course, Listing, ListingDetail } from "../types.ts";
import { IconArrowLeft, IconCheck, IconSearch, IconTag } from "./icons.tsx";

interface MarketplaceProps {
  listings: Listing[];
  loading: boolean;
  error: string | null;
  query: string;
  onQueryChange: (q: string) => void;
  onBought: (course: Course) => void;
}

export default function Marketplace({ listings, loading, error, query, onQueryChange, onBought }: MarketplaceProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (selectedId) {
    return <ListingDetailView listingId={selectedId} onBack={() => setSelectedId(null)} onBought={onBought} />;
  }

  return (
    <div className="marketplace">
      <div className="courses-list-head">
        <h2>Marketplace</h2>
      </div>
      <p className="hint marketplace-intro">
        Curricula built and priced by other teachers. Buying gives you your own editable copy —
        review it, make it yours, and publish it to your own students.
      </p>

      <div className="marketplace-search">
        <IconSearch className="marketplace-search-icon" />
        <input
          type="search"
          className="auth-input marketplace-search-input"
          placeholder="Search by title or topic…"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
        />
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <p className="hint">Loading…</p>
      ) : listings.length === 0 ? (
        <p className="hint">No listings match yet. Try a different search, or check back later.</p>
      ) : (
        <div className="course-card-grid">
          {listings.map((listing) => (
            <button type="button" className="listing-card" key={listing.id} onClick={() => setSelectedId(listing.id)}>
              <div className="listing-card-top">
                <h3>{listing.title}</h3>
                <span className="listing-price"><IconTag /> {formatPrice(listing.priceCents)}</span>
              </div>
              <p className="course-card-audience">by {listing.sellerName}{listing.audience ? ` · ${listing.audience}` : ""}</p>
              <p className="listing-description">{listing.description || "No description yet."}</p>
              <span className="course-card-meta">
                {listing.weekCount} week{listing.weekCount === 1 ? "" : "s"} · {listing.lessonCount} lesson
                {listing.lessonCount === 1 ? "" : "s"}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

interface ListingDetailViewProps {
  listingId: string;
  onBack: () => void;
  onBought: (course: Course) => void;
}

function ListingDetailView({ listingId, onBack, onBought }: ListingDetailViewProps) {
  const [listing, setListing] = useState<ListingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [buying, setBuying] = useState(false);
  const [bought, setBought] = useState<Course | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchListing(listingId)
      .then((data) => { if (!cancelled) setListing(data); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); });
    return () => { cancelled = true; };
  }, [listingId]);

  async function handleBuy() {
    setBuying(true);
    setError(null);
    try {
      const course = await buyListing(listingId);
      setBought(course);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBuying(false);
    }
  }

  return (
    <div className="marketplace">
      <button type="button" className="btn listing-back" onClick={onBack}>
        <IconArrowLeft /> Back to Marketplace
      </button>

      {error && <div className="error-banner">{error}</div>}

      {!listing ? (
        <p className="hint">Loading…</p>
      ) : bought ? (
        <div className="listing-bought">
          <span className="status-pill status-published listing-bought-badge"><IconCheck /> Purchased</span>
          <h2>{bought.title} is now yours</h2>
          <p className="hint">
            It's in My Courses as a draft — review it, make any changes, and publish it to your own students
            whenever you're ready.
          </p>
          <button type="button" className="btn btn-primary" onClick={() => onBought(bought)}>
            Open in My Courses
          </button>
        </div>
      ) : (
        <div className="listing-detail">
          <div className="listing-detail-head">
            <div>
              <h2>{listing.title}</h2>
              <p className="course-card-audience">
                by {listing.sellerName}{listing.audience ? ` · ${listing.audience}` : ""}
              </p>
            </div>
            <span className="listing-price listing-price-lg">{formatPrice(listing.priceCents)}</span>
          </div>

          <p className="panel-objective">{listing.description || "No description yet."}</p>

          <label className="field-label">Syllabus preview</label>
          <div className="listing-outline">
            {listing.weeks.map((w) => (
              <div className="week-block" key={w.week}>
                <div className="week-head">
                  <span className="week-head-title">Week {w.week} — {w.title}</span>
                  <span className="week-head-count">{w.lessons.length}</span>
                </div>
                <ul className="hitl-lesson-list">
                  {w.lessons.map((l, i) => <li key={i}>{l.title}</li>)}
                </ul>
              </div>
            ))}
          </div>
          <p className="hint-inline">
            Full slides, speaker notes, and quizzes unlock after purchase.
          </p>

          <button type="button" className="btn btn-primary listing-buy" onClick={handleBuy} disabled={buying}>
            {buying ? "Purchasing…" : `Buy for ${formatPrice(listing.priceCents)}`}
          </button>
        </div>
      )}
    </div>
  );
}
