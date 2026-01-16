import { useRef, useState } from 'react';
import { UploadCloud } from 'lucide-react';
import styles from './DropZone.module.css';

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
        e.target.value = '';
      }
    }
  };

  return (
    <div
      className={`${styles.dropArea} ${isDragging ? styles.dragging : ''}`}
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
        className={styles.fileInput}
        multiple
        accept=".pdf,.txt,.docx,.jpeg,.jpg,.png"
      />

      <div className={styles.iconWrapper}>
        <UploadCloud size={34} color="white" />
      </div>

      <p className={styles.mainText}>Click to upload or drag and drop</p>
      <p className={styles.subText}>PDF, TXT, DOCX, JPEG, JPG, PNG</p>
    </div>
  );
};

export default DropZone;
