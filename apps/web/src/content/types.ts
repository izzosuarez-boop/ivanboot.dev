// Shapes of the portfolio content, shared by the English (Upwork) and Spanish (Workana) versions.

export type ProjectStatus = "Live demo" | "Case study" | "In progress";

export type Project = {
  title: string;
  status: ProjectStatus;
  summary: string | string[];  // paragraphs; "[[link]]" places the link button inline
  problem: string;
  how: string;
  result: string;
  stack: string[];
  link?: { label: string; href: string };
  repos?: { label: string; href: string }[];  // GitHub repos with this project's code
  demoHref?: string;            // makes the status badge a button that opens the live demo
  video?: { media: string; title: string };  // key in portfolio-media.json, shown instead of screenshots
  loop?: { media: string; label: string };   // key in portfolio-loops.json: a 6 s silent loop, shown first
  image?: string | null;
};

export type Section = {
  slug: string;
  label: string;      // section name (page header, links), also on the circle unless `ring` is set
  ring?: string;      // shorter text on the circle when `label` doesn't fit a segment
  short: string;      // compact label for small screens
  pitch: string;      // headline inside the section
  intro: string;
  // big section video above the projects; media: key in portfolio-media.json. Leave it out to show no panel at all
  video?: { title: string; media?: string; src?: string | null };
  projects: Project[];
};

export type HubIntro = { eyebrow: string; title: string; videoTitle: string; media: string };

export type About = {
  name: string;
  role: string;
  bio: string;
  education: { title: string; place: string; years: string }[];
  highlights: string[];
  skills: string[];
};

// Interface text that isn't content: buttons, labels, headings
export type Ui = {
  srTitle: string;           // the hub's hidden <h1>
  roleLine: string;          // under the name, top left of the hub
  allWork: string;
  hire: string;              // the hiring button
  hireTitle: string;
  hireBody: string;
  chooseArea: string;
  aboutMe: string;
  aboutOf: (name: string) => string;
  sceneAlt: (name: string) => string;
  portraitAlt: (name: string) => string;
  close: string;
  education: string;
  highlights: string;
  skills: string;
  introVideo: string;
  explainerVideo: string;
  projects: string;
  otherAreas: string;
  areasOfWork: string;
  problem: string;
  how: string;
  result: string;
  status: Record<ProjectStatus, string>;
  screenshotsSoon: string;
  videoSoon: string;
  onGithub: (label: string) => string;
  player: { voice: string; subtitles: string; tapForSound: string; fullScreen: string; exitFullScreen: string; off?: string };
};

export type Content = { lang: "en" | "es"; sections: Section[]; hubIntro: HubIntro; about: About; ui: Ui };
