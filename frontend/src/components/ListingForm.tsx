import { useState, type FormEvent } from "react";
import { createListing } from "../api.ts";
import { formatPrice } from "../format.ts";
import type { Course, Listing } from "../types.ts";
import { IconClose } from "./icons.tsx";

interface ListingFormProps {
  course: Course;
  onClose: () => void;
  onCreated: (listing: Listing) => void;
}

export default function ListingForm({ course, onClose, onCreated }: ListingFormProps) {
  const [title, setTitle] = useState(course.title);
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("19.99");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const dollars = Number(price);
    if (!Number.isFinite(dollars) || dollars <= 0) {
      setError("Enter a price greater than $0.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const listing = await createListing({
        courseId: course.id,
        title,
        description,
        priceCents: Math.round(dollars * 100),
      });
      onCreated(listing);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span>List on Marketplace</span>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            <IconClose />
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="listing-title">Title</label>
          <input
            id="listing-title"
            className="auth-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />

          <label className="field-label" htmlFor="listing-description">Description</label>
          <textarea
            id="listing-description"
            className="auth-input modal-textarea"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What will another teacher get, and who is it for?"
            rows={4}
          />

          <label className="field-label" htmlFor="listing-price">Price (USD)</label>
          <input
            id="listing-price"
            className="auth-input"
            type="number"
            min="1"
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            required
          />
          <span className="hint-inline">Buyers will see {formatPrice(Math.round((Number(price) || 0) * 100))}.</span>

          {error && <div className="error-banner auth-error">{error}</div>}

          <button type="submit" className="btn btn-primary auth-submit" disabled={submitting}>
            {submitting ? "Listing…" : "List for sale"}
          </button>
        </form>
      </div>
    </div>
  );
}
