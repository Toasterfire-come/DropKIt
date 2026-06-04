import React from "react";
import { Composition } from "remotion";
import { Shot1WalletCommunity } from "./Shots/Shot1WalletCommunity";
import { Shot2ProgressBar } from "./Shots/Shot2ProgressBar";
import { Shot3CalendarCountdown } from "./Shots/Shot3CalendarCountdown";
import { Shot4ThreeIcons } from "./Shots/Shot4ThreeIcons";
import { Shot5CardBullets } from "./Shots/Shot5CardBullets";
import { Shot6StepFlow } from "./Shots/Shot6StepFlow";
import { LogoIntro } from "./Shots/LogoIntro";

const FPS = 30;
const HOLD_FRAMES = 2 * FPS; // 2 second hold

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="Shot1-WalletCommunity"
        component={Shot1WalletCommunity}
        durationInFrames={5 * FPS + HOLD_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
      />
      <Composition
        id="Shot2-ProgressBar"
        component={Shot2ProgressBar}
        durationInFrames={4 * FPS + HOLD_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
      />
      <Composition
        id="Shot3-CalendarCountdown"
        component={Shot3CalendarCountdown}
        durationInFrames={4 * FPS + HOLD_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
      />
      <Composition
        id="Shot4-ThreeIcons"
        component={Shot4ThreeIcons}
        durationInFrames={5 * FPS + HOLD_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
      />
      <Composition
        id="Shot5-CardBullets"
        component={Shot5CardBullets}
        durationInFrames={5 * FPS + HOLD_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
      />
      <Composition
        id="Shot6-StepFlow"
        component={Shot6StepFlow}
        durationInFrames={5 * FPS + HOLD_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
      />
      <Composition
        id="LogoIntro"
        component={LogoIntro}
        durationInFrames={3 * FPS}
        fps={FPS}
        width={1080}
        height={1920}
      />
    </>
  );
};