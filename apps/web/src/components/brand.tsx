import Link from "next/link";

export function Brand() {
  return (
    <Link className="flex items-center gap-3" href="/" aria-label="Rayo Finanças">
      <span className="grid size-10 place-items-center rounded-[14px] bg-[#173f35] shadow-[0_8px_24px_rgba(23,63,53,.18)]">
        <svg aria-hidden="true" className="size-6" viewBox="0 0 32 32" fill="none">
          <path
            d="M7 23V15.8c0-.6.3-1.2.8-1.5l7-4.7c.7-.5 1.7-.5 2.4 0l7 4.7c.5.3.8.9.8 1.5V23"
            stroke="#D9FF65"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M11.5 23v-5h9v5"
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <span className="text-[1.05rem] font-bold tracking-[-0.03em] text-[#173f35]">
        rayo
      </span>
    </Link>
  );
}
