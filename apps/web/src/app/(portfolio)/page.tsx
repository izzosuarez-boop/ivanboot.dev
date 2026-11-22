import { HubCenter } from "./_components/hub-center";

// The hub: the circle (drawn by the layout's shell) with the scene in the middle.
export default function Home() {
  return (
    <main className="h-svh overflow-hidden">
      <h1 className="sr-only">Iván — AI agents, automation and full-stack development</h1>
      <HubCenter />
    </main>
  );
}
