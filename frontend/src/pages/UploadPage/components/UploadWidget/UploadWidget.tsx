import DropZone from "../DropZone/DropZone";
import RecommendedList from "../RecommendedList/RecommendedList";

interface UploadWidgetProps {
  onFilesSelected: (files: File[]) => void;
}

const UploadWidget = ({ onFilesSelected }: UploadWidgetProps) => {
  return (
    <div
      className="
      w-full
      flex
      flex-col
      items-center
      p-[1.75rem]
      rounded-[14px]
      border
      border-(--card-border)
      bg-(--card-bg)
      backdrop-blur-[10px]
      shadow-[0_4px_30px_rgba(0,0,0,0.1)]
    "
    >
      <DropZone onFilesSelected={onFilesSelected} />

      <div className="w-full flex justify-center my-4">
        <div className="w-[80%] h-px bg-white/10" />
      </div>

      <div className="w-full flex flex-col items-center">
        <h3
          className="
          text-[0.85rem]
          font-medium
          text-(--text-primary)
          mb-[0.7rem]
        "
        >
          Recommended Documents
        </h3>

        <div className="w-[75%] flex justify-center">
          <RecommendedList />
        </div>
      </div>
    </div>
  );
};

export default UploadWidget;
