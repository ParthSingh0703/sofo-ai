import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

interface TopicSectionProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

const TopicSection = ({
  title,
  children,
  defaultOpen = false,
}: TopicSectionProps) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div
      className="
      w-full
      border-b border-(--card-border)
      mb-2
    "
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="
        w-full
        flex items-center justify-between
        py-[0.4rem]
        text-(--text-secondary)
        transition-colors duration-200 ease
        cursor-pointer
        hover:text-(--text-primary)
      "
      >
        <div>
          <span
            className="
            text-[0.65rem]
            font-semibold
            uppercase
            tracking-[0.05em]
          "
          >
            {title}
          </span>
        </div>

        {isOpen ? (
          <ChevronDown size={16} className="opacity-70" />
        ) : (
          <ChevronRight size={16} className="opacity-70" />
        )}
      </button>

      <div
        className={`
        overflow-hidden
        transition-[max-height,padding,opacity]
        duration-300
        ease-out
        opacity-0
        max-h-0
        ${isOpen ? "max-h-[2000px] pb-[0.8rem] opacity-100" : ""}
      `}
      >
        <div
          className="
          grid
          grid-cols-[repeat(auto-fill,minmax(130px,1fr))]
          gap-x-[0.8rem] gap-y-[0.6rem]
          pt-[0.1rem]
          items-start
        "
        >
          {children}
        </div>
      </div>
    </div>
  );
};

export default TopicSection;
