import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import styles from './TopicSection.module.css';

interface TopicSectionProps {
    title: string;
    children: React.ReactNode;
    defaultOpen?: boolean;
}

const TopicSection = ({ title, children, defaultOpen = false }: TopicSectionProps) => {
    const [isOpen, setIsOpen] = useState(defaultOpen);

    return (
        <div className={styles.section}>
            <button
                className={styles.header}
                onClick={() => setIsOpen(!isOpen)}
            >
                <div className={styles.titleWrapper}>
                    <span className={styles.title}>{title}</span>
                </div>
                {isOpen ? <ChevronDown size={16} className={styles.icon} /> : <ChevronRight size={16} className={styles.icon} />}
            </button>

            <div className={`${styles.content} ${isOpen ? styles.open : ''}`}>
                <div className={styles.grid}>
                    {children}
                </div>
            </div>
        </div>
    );
};

export default TopicSection;
