import { PromptBox } from "./shared/PromptBox";

export function FloatingPrompt() {
  return (
    <div className="w-full h-screen bg-[#fcfcfc] dark:bg-[#1a1a1a] flex items-center justify-center p-4">
      <PromptBox />
    </div>
  );
}
