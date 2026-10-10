// Pre-filling company / sender / role from what the student pasted. Pure, so it can be unit-tested.

export interface Fields {
  company: string;
  sender: string;
  role: string;
}
export type Auto = { company: boolean; sender: boolean; role: boolean };
export interface Detected {
  company: string | null;
  sender_email: string | null;
  role: string | null;
}

export const NO_AUTO: Auto = { company: false, sender: false, role: false };

/**
 * Fill each field from the detection, but never overwrite something the student typed or picked:
 * a field is replaced only if it is empty or was itself auto-filled. A field the detection no longer
 * finds (the text changed) is cleared, but only if it was auto-filled.
 */
export function applyDetected(fields: Fields, auto: Auto, d: Detected | null): { fields: Fields; auto: Auto } {
  const next = { ...fields };
  const nextAuto = { ...auto };
  const pairs: [keyof Fields, keyof Auto, string | null][] = [
    ["company", "company", d?.company ?? null],
    ["sender", "sender", d?.sender_email ?? null],
    ["role", "role", d?.role ?? null],
  ];
  for (const [field, flag, found] of pairs) {
    if (fields[field] === "" || auto[flag]) {
      next[field] = found ?? "";
      nextAuto[flag] = Boolean(found);
    }
  }
  return { fields: next, auto: nextAuto };
}

/** "company, sender email and role": which fields were filled for the student. */
export function describeAuto(auto: Auto): string {
  const names = [auto.company && "company", auto.sender && "sender email", auto.role && "role"].filter(Boolean) as string[];
  return names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}` : names[0] ?? "";
}
