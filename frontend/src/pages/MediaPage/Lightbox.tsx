import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useEffect } from 'react';
import styles from './Lightbox.module.css';

interface LightboxProps {
    images: Array<{ src: string; room: string; description: string }>;
    currentIndex: number;
    onClose: () => void;
    onNext: () => void;
    onPrev: () => void;
}

const Lightbox = ({ images, currentIndex, onClose, onNext, onPrev }: LightboxProps) => {
    const currentImage = images[currentIndex];

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
            if (e.key === 'ArrowRight') onNext();
            if (e.key === 'ArrowLeft') onPrev();
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose, onNext, onPrev]);

    if (!currentImage) return null;

    return (
        <div className={styles.overlay}>
            <button className={styles.closeButton} onClick={onClose}>
                <X size={24} />
            </button>

            <div className={styles.mainContent}>
                <button className={`${styles.navButton} ${styles.prev}`} onClick={onPrev}>
                    <ChevronLeft size={32} />
                </button>

                <img
                    src={currentImage.src}
                    alt={currentImage.room}
                    className={styles.image}
                />

                <div className={styles.footer}>
                    <h3 className={styles.roomTitle}>{currentImage.room}</h3>
                    <p className={styles.roomDesc}>{currentImage.description}</p>
                </div>

                <button className={`${styles.navButton} ${styles.next}`} onClick={onNext}>
                    <ChevronRight size={32} />
                </button>
            </div>
        </div>
    );
};

export default Lightbox;
