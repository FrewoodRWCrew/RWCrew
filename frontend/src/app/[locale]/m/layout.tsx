// The phone section of the app ("/m/..."): what the installed PWA opens
// (see app/manifest.ts). It shows only the screens the old phone app had,
// in a single narrow column, without the desktop sidebar or top bar. The
// login check lives one level down in (signed-in)/layout.tsx, so the
// phone's own login page (login/page.tsx) can sit next to it.

export default function PhoneLayout({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto flex min-h-dvh w-full max-w-lg flex-col bg-background">{children}</div>;
}
