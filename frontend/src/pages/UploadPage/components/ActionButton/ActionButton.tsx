

interface ActionButtonProps {
  isActive: boolean;
  onClick: () => void;
  isLoading?: boolean;
}

const ActionButton = ({
  isActive,
  onClick,
  isLoading = false,
}: ActionButtonProps) => {
  return (
    <button
      className={`
      w-full
      p-[0.7rem]
      rounded-[9px]
      text-[1.2rem]
      font-medium
      text-white
      mt-[0.7rem]
      transition-all duration-300
      ${
        isActive
          ? "bg-(--accent-blue) shadow-[0_4px_12px_rgba(37,99,235,0.3)] hover:bg-(--accent-blue-hover) hover:-translate-y-[1px]"
          : "bg-[rgba(37,99,235,0.2)] text-[rgba(255,255,255,0.4)] cursor-not-allowed"
      }
    `}
      disabled={!isActive || isLoading}
      onClick={onClick}
    >
      {isLoading ? "Starting..." : "Start AI Engine"}
    </button>
  );
};

export default ActionButton;
