import { useEffect, useRef } from 'react';

type HelpDrawerProps = {
  open: boolean;
  title: string;
  analogy: string;
  bullets: string[];
  onClose: () => void;
};

const HelpDrawer = ({ open, title, analogy, bullets, onClose }: HelpDrawerProps) => {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const previouslyFocused = document.activeElement as HTMLElement | null;

    const focusFirst = () => {
      const focusable = ref.current?.querySelector<HTMLElement>('button, [href], [tabindex="0"]');
      focusable?.focus();
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    setTimeout(focusFirst, 0);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <aside className="help-drawer" aria-label={`${title} help`} ref={ref} role="dialog" aria-modal="true">
      <header className="help-drawer__header">
        <h2>{title}</h2>
        <button type="button" className="btn btn--ghost" onClick={onClose} aria-label="Close help">
          Close
        </button>
      </header>
      <p className="help-drawer__analogy">{analogy}</p>
      <h3>How to read these numbers</h3>
      <ul>
        {bullets.map((bullet, index) => (
          <li key={index}>{bullet}</li>
        ))}
      </ul>
    </aside>
  );
};

export default HelpDrawer;
