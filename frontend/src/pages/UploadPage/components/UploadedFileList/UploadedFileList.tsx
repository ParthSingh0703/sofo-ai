import { CheckCircle2, XCircle, Trash2 } from "lucide-react";

interface FileItem {
  id: string | number;
  name: string;
  size: string;
  status: "success" | "error" | "uploading";
  documentId?: string;
  imageId?: string;
  isImage?: boolean;
}

interface UploadedFileListProps {
  files: FileItem[];
  onDelete: (file: FileItem) => void;
}

const UploadedFileList = ({ files, onDelete }: UploadedFileListProps) => {
  return (
    <div className="flex flex-col gap-[0.1rem] w-full">
      {files.map((file) => (
        <div
          key={file.id}
          className="
          flex items-center justify-between
          py-[0.15rem]
          border-b border-white/5
          last:border-b-0
        "
        >
          <div className="flex items-center gap-[0.3rem] overflow-hidden">
            {file.status === "success" ? (
              <CheckCircle2
                size={13}
                className="text-(--success-green) shrink-0"
              />
            ) : (
              <XCircle size={13} className="text-(--error-red) shrink-0" />
            )}

            <span
              className="
              text-[0.65rem]
              font-medium
              truncate
              max-w-[210px]
            "
              style={{
                color:
                  file.status === "success"
                    ? "var(--success-green)"
                    : "var(--error-red)",
              }}
            >
              {file.name}
            </span>

            <span className="text-[0.6rem] text-gray-500">{file.size}</span>
          </div>

          <button
            onClick={() => onDelete(file)}
            disabled={file.status === "uploading"}
            aria-label={`Delete ${file.name}`}
            className="
            p-[0.25rem]
            flex items-center justify-center
            text-white/50
            transition-colors duration-200
            shrink-0
            hover:text-(--error-red)
            disabled:cursor-not-allowed
            disabled:opacity-30
          "
          >
            <Trash2 size={12} />
          </button>
        </div>
      ))}
    </div>
  );
};

export default UploadedFileList;
