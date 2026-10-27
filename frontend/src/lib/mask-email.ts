// Hides most of an email address before it is shown on screen (GDPR): the
// desk can still recognise "fr***@gm***.com", but can't read the full
// address. The database and the mails keep the real address; only the
// display goes through here.

/** The start of a part: its first 2 characters (1 for a part of 1–2) + "***". */
function maskPart(part: string): string {
  const visible = part.length > 2 ? part.slice(0, 2) : part.slice(0, 1);
  return `${visible}***`;
}

/** "frederik@gmail.com" → "fr***@gm***.com"; anything odd → "***". */
export function maskEmail(email: string): string {
  const value = email.trim();
  const at = value.lastIndexOf("@");
  // No "@", or nothing before/after it: show nothing of it.
  if (at <= 0 || at === value.length - 1) return "***";
  const local = value.slice(0, at);
  const domain = value.slice(at + 1);
  // The domain's last part (".com", ".be") stays visible; the name before it is hidden.
  const dot = domain.lastIndexOf(".");
  if (dot <= 0 || dot === domain.length - 1) return `${maskPart(local)}@***`;
  return `${maskPart(local)}@${maskPart(domain.slice(0, dot))}${domain.slice(dot)}`;
}
