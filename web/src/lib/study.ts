/** The Study hub's section cards. `subject` is the catalog subject slug used to link into Practice. */
export const STUDY_SECTIONS = [
  {
    slug: "formulas",
    title: "Mathematics formulas",
    titleBn: "গণিতের সূত্র",
    blurb: "Quick reference cards for the formulas used in the worked solutions.",
    endpoint: "/formulas/",
    subject: "mathematics",
    icon: "∑",
  },
  {
    slug: "rules",
    title: "Grammar rules",
    titleBn: "ব্যাকরণের নিয়ম",
    blurb: "The grammar and usage rules behind sentence correction and error spotting.",
    endpoint: "/rules/",
    subject: "language",
    icon: "Aa",
  },
] as const;
