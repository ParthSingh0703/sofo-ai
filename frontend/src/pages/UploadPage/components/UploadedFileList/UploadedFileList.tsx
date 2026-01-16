import { CheckCircle2, XCircle, Trash2 } from 'lucide-react';
import styles from './UploadedFileList.module.css';

interface FileItem {
  id: string | number;
  name: string;
  size: string;
  status: 'success' | 'error' | 'uploading';
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
    <div className={styles.list}>
      {files.map((file) => (
        <div key={file.id} className={styles.row}>
          <div className={styles.left}>
            {file.status === 'success' ? (
              <CheckCircle2 className={styles.successIcon} size={13} />
            ) : (
              <XCircle className={styles.errorIcon} size={13} />
            )}

            <span
              className={styles.fileName}
              style={{ color: file.status === 'success' ? 'var(--success-green)' : 'var(--error-red)' }}
            >
              {file.name}
            </span>

            <span className={styles.fileSize}>{file.size}</span>
          </div>
          
          <button
            onClick={() => onDelete(file)}
            className={styles.deleteButton}
            disabled={file.status === 'uploading'}
            aria-label={`Delete ${file.name}`}
          >
            <Trash2 size={12} />
          </button>
        </div>
      ))}
    </div>
  );
};

export default UploadedFileList;
