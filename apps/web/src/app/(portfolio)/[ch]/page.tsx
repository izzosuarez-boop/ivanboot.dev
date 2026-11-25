import { notFound } from "next/navigation";
import { HubCenter } from "../_components/hub-center";
import { channelOf, channelSite } from "@/content/channel";

// The hub: the circle (drawn by the layout's shell) with the scene in the middle, and the intro video.
export default async function Home({ params }: PageProps<"/[ch]">) {
  const ch = channelOf((await params).ch);
  if (!ch) notFound();
  const site = channelSite(ch);
  const { ui, about } = site;
  return (
    <main className="relative min-h-svh">
      <h1 className="sr-only">{ui.srTitle}</h1>
      <HubCenter
        about={about}
        hubIntro={site.hubIntro}
        pitches={site.sections.map((s) => s.pitch)}
        intro={site.media(site.hubIntro.media)}
        ui={{
          chooseArea: ui.chooseArea, aboutMe: ui.aboutMe, close: ui.close, education: ui.education,
          highlights: ui.highlights, skills: ui.skills, introVideo: ui.introVideo, player: ui.player,
          aboutOf: ui.aboutOf(about.name), sceneAlt: ui.sceneAlt(about.name), portraitAlt: ui.portraitAlt(about.name),
        }}
      />
    </main>
  );
}
