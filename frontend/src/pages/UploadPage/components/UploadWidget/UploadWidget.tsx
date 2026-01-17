import DropZone from '../DropZone/DropZone';
import RecommendedList from '../RecommendedList/RecommendedList';
import styles from './UploadWidget.module.css';

interface UploadWidgetProps {
  onFilesSelected: (files: File[]) => void;
}

const UploadWidget = ({ onFilesSelected }: UploadWidgetProps) => {
  return (
    <div className={styles.container}>
      <DropZone onFilesSelected={onFilesSelected} />

      <div className={styles.separatorContainer}>
        <div className={styles.separator} />
      </div>

      <div className={styles.recommendedSection}>
        <h3 className={styles.recommendedTitle}>Recommended Documents</h3>
        <div className={styles.recommendedListWrapper}>
          <RecommendedList />
        </div>
      </div>
    </div>
  );
};

export default UploadWidget;
