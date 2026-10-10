import { Checker } from "./components/Checker";
import { Footer } from "./components/Footer";
import { Hero } from "./components/Hero";
import { HowItWorks } from "./components/HowItWorks";

export default function App() {
  return (
    <>
      <Hero />
      <main>
        <Checker />
        <HowItWorks />
      </main>
      <Footer />
    </>
  );
}
