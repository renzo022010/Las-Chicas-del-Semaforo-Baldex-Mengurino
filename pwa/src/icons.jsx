// Iconos de trazo simple (24x24) para no depender de librerias externas.
const PATHS = {
  back: <path d="M15 5l-7 7 7 7" />,
  home: <><path d="M4 11l8-7 8 7" /><path d="M6 10v10h12V10" /></>,
  flask: <><path d="M9 3h6" /><path d="M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3" /><path d="M7.5 15h9" /></>,
  plus: <><circle cx="12" cy="12" r="9" /><path d="M12 8v8M8 12h8" /></>,
  dish: <><circle cx="12" cy="12" r="8.5" /><circle cx="9.5" cy="10" r="1.2" /><circle cx="14" cy="9" r="1" /><circle cx="14.5" cy="14" r="1.4" /><circle cx="10" cy="15" r="1" /></>,
  doc: <><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v4h4" /><path d="M9.5 12h5M9.5 15h5M9.5 18h3" /></>,
  calc: <><rect x="5" y="3" width="14" height="18" rx="2" /><path d="M8 7h8" /><path d="M8.5 11h.01M12 11h.01M15.5 11h.01M8.5 14.5h.01M12 14.5h.01M15.5 14.5h.01M8.5 18h.01M12 18h.01M15.5 18h.01" /></>,
  camera: <><path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.5" /></>,
  image: <><rect x="4" y="5" width="16" height="14" rx="2" /><circle cx="9" cy="10" r="1.5" /><path d="M5 17l5-5 4 4 2-2 3 3" /></>,
  pdf: <><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v4h4" /><path d="M9 16v-4h1.5a1.5 1.5 0 0 1 0 3H9" /></>,
  chevron: <path d="M9 5l7 7-7 7" />,
  trash: <><path d="M5 7h14" /><path d="M10 7V4h4v3" /><path d="M7 7l1 13h8l1-13" /></>,
  check: <path d="M5 12l5 5 9-10" />,
  undo: <><path d="M9 7L5 11l4 4" /><path d="M5 11h9a5 5 0 0 1 0 10h-3" /></>,
  zoom: <><circle cx="11" cy="11" r="6.5" /><path d="M16 16l4 4M11 8v6M8 11h6" /></>,
}

export function Icon({ name, size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {PATHS[name]}
    </svg>
  )
}
