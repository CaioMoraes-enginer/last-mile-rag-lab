import { useState, type ReactNode } from "react";

/** Chip generico (rotulo colorido). */
export function Chip({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <span className={`chip ${className}`}>{children}</span>;
}

/** Chip de classe de risco, com a cor do enum (STANDARD..BREACH). */
export function RiskChip({ risk }: { risk: string | null }) {
  if (!risk) return <Chip className="risk-STANDARD">sem risco</Chip>;
  return <Chip className={`risk-${risk}`}>{risk.replace("_", " ")}</Chip>;
}

/** Barra de progresso 0..1 (usada para confianca). */
export function Bar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="confbar">
      <span style={{ width: `${pct}%` }} />
    </div>
  );
}

/** Secao colapsavel com contador. */
export function Section({
  title,
  count,
  defaultOpen = false,
  children,
}: {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`section ${open ? "open" : ""}`}>
      <button className="section-head" onClick={() => setOpen((o) => !o)}>
        <span className="section-title">
          {title}
          {count !== undefined && <span className="count">{count}</span>}
        </span>
        <span className="chev">▶</span>
      </button>
      {open && <div className="section-content">{children}</div>}
    </div>
  );
}
