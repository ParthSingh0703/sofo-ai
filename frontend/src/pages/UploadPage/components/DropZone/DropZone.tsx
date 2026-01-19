import { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
interface DropZoneProps {
  onFilesSelected: (files: File[]) => void;
}

const DropZone = ({ onFilesSelected }: DropZoneProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFilesSelected(Array.from(e.dataTransfer.files));
      e.dataTransfer.clearData();
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFilesSelected(Array.from(e.target.files));
      // Reset input value to allow selecting the same file again
      if (e.target) {
        e.target.value = "";
      }
    }
  };

  return (
    <div
      className={`
      w-full
      flex flex-col
      items-center justify-center
      cursor-pointer
      transition-[transform,opacity] duration-200
      rounded-[8px]
      border-2 border-transparent
      ${isDragging ? "border-(--accent-blue) bg-[rgba(37,99,235,0.1)]" : ""}
    `}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInput}
        className="hidden"
        multiple
        accept=".pdf,.txt,.docx,.jpeg,.jpg,.png"
      />

      <div className="mb-[0.7rem]">
        <UploadCloud size={34} color="white" />
      </div>

      <p className="text-[1.2rem] font-semibold text-(--text-primary) mb-[0.35rem]">
        Click to upload or drag and drop
      </p>

      <p className="text-[0.9rem] text-(--text-secondary) uppercase">
        PDF, TXT, DOCX, JPEG, JPG, PNG
      </p>
    </div>
  );
};

export default DropZone;
