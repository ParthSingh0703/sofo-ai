import styles from './ActionButton.module.css';

interface ActionButtonProps {
  isActive: boolean;
  onClick: () => void;
  isLoading?: boolean;
}

const ActionButton = ({ isActive, onClick, isLoading = false }: ActionButtonProps) => {
  return (
    <button
      className={`${styles.button} ${isActive ? styles.active : styles.inactive}`}
      disabled={!isActive || isLoading}
      onClick={onClick}
    >
      {isLoading ? 'Starting...' : 'Start AI Engine'}
    </button>
  );
};

export default ActionButton;
