import BuiltWith from "./components/BuiltWith.tsx";
import Capabilities from "./components/Capabilities.tsx";
import CtaBand from "./components/CtaBand.tsx";
import FeatureShowcase from "./components/FeatureShowcase.tsx";
import Footer from "./components/Footer.tsx";
import Hero from "./components/Hero.tsx";
import Nav from "./components/Nav.tsx";
import Outcomes from "./components/Outcomes.tsx";
import PricingResources from "./components/PricingResources.tsx";
import TrustStatement from "./components/TrustStatement.tsx";
import WhoItsFor from "./components/WhoItsFor.tsx";

export default function App() {
  return (
    <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <Nav />
      <main id="main-content">
        <Hero />
        <BuiltWith />
        <FeatureShowcase />
        <WhoItsFor />
        <Outcomes />
        <TrustStatement />
        <Capabilities />
        <PricingResources />
        <CtaBand />
      </main>
      <Footer />
    </>
  );
}
