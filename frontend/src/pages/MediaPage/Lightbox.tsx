import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect } from "react";

interface LightboxProps {
  images: Array<{ src: string; room: string; description: string }>;
  currentIndex: number;
  onClose: () => void;
  onNext: () => void;
  onPrev: () => void;
}

const Lightbox = ({
  images,
  currentIndex,
  onClose,
  onNext,
  onPrev,
}: LightboxProps) => {
  const currentImage = images[currentIndex];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") onNext();
      if (e.key === "ArrowLeft") onPrev();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, onNext, onPrev]);

  if (!currentImage) return null;

  return (
    <div
      className="
      fixed inset-0
      bg-black/95
      z-[1000]
      flex flex-col items-center justify-center
      animate-[fadeIn_0.2s_ease-out]
    "
    >
      <button
        onClick={onClose}
        className="
        absolute top-[20px] right-[20px]
        w-[40px] h-[40px]
        rounded-full
        bg-white/10
        border-none
        text-white
        cursor-pointer
        flex items-center justify-center
        transition-colors duration-200
        hover:bg-white/20
        z-[1001]
      "
      >
        <X size={24} />
      </button>

      <div
        className="
        flex-1 w-full h-full
        flex flex-col items-center justify-center
        relative
        p-[40px]
        gap-[20px]
      "
      >
        <button
          onClick={onPrev}
          className="
          w-[50px] h-[50px]
          rounded-full
          bg-white
          border-none
          text-black
          cursor-pointer
          flex items-center justify-center
          absolute top-1/2 left-[40px]
          -translate-y-1/2
          transition-transform duration-200
          opacity-80
          hover:scale-110 hover:opacity-100
          z-[1002]
        "
        >
          <ChevronLeft size={32} />
        </button>

        <img
          src={currentImage.src}
          alt={currentImage.room}
          className="
          max-w-[90%]
          max-h-[55vh]
          object-contain
          rounded-lg
          shadow-[0_20px_50px_rgba(0,0,0,0.5)]
        "
        />

        <div className="w-full text-center text-white">
          <h3 className="text-[1.2rem] font-semibold mb-2">
            {currentImage.room}
          </h3>
          <p className="text-[0.9rem] text-white/70 italic">
            {currentImage.description}
          </p>
        </div>

        <button
          onClick={onNext}
          className="
          w-[50px] h-[50px]
          rounded-full
          bg-white
          border-none
          text-black
          cursor-pointer
          flex items-center justify-center
          absolute top-1/2 right-[40px]
          -translate-y-1/2
          transition-transform duration-200
          opacity-80
          hover:scale-110 hover:opacity-100
          z-[1002]
        "
        >
          <ChevronRight size={32} />
        </button>
      </div>
    </div>
  );
};

export default Lightbox;
