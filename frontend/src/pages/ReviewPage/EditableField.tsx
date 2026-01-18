import { useState, useEffect, useRef } from 'react';
import { Pencil } from 'lucide-react';
import styles from './EditableField.module.css';

interface EditableFieldProps {
    label: string;
    value: string | number | null | undefined;
    onSave: (value: string) => void;
    forceEdit?: boolean;
    multiline?: boolean;
    height?: string;
}

const EditableField = ({ label, value, onSave, forceEdit = false, multiline = false, height = 'auto' }: EditableFieldProps) => {
    // Local editing state for non-forced mode
    const [localEditing, setLocalEditing] = useState(false);
    // When forceEdit is true, use it; otherwise use local state
    const isEditing = forceEdit || localEditing;
    const [currentValue, setCurrentValue] = useState(String(value || ''));
    const inputRef = useRef<HTMLInputElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const previousValueRef = useRef<string>(String(value || ''));

    const adjustTextareaHeight = () => {
        const el = textareaRef.current;
        if (el) {
            el.style.height = 'auto';
            el.style.height = el.scrollHeight + 'px';
        }
    };

    useEffect(() => {
        if (isEditing) {
            if (multiline && textareaRef.current) {
                textareaRef.current.focus();
                adjustTextareaHeight();
            } else if (inputRef.current) {
                inputRef.current.focus();
            }
        }
    }, [isEditing, multiline]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setCurrentValue(e.target.value);
        if (multiline) {
            adjustTextareaHeight();
        }
    };

    const handleClick = () => {
        if (!forceEdit) {
            setLocalEditing(true);
        }
    };

    const handleBlur = () => {
        if (!forceEdit) {
            setLocalEditing(false);
            if (onSave) onSave(currentValue);
        } else {
            if (onSave) onSave(currentValue);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && !multiline) {
            if (!forceEdit) {
                handleBlur();
            } else {
                if (onSave) onSave(currentValue);
                inputRef.current?.blur();
            }
        }
    };

    // Sync currentValue with value prop only when not editing and value actually changed
    // Using requestAnimationFrame to avoid synchronous setState in effect
    useEffect(() => {
        const newValue = String(value || '');
        if (newValue !== previousValueRef.current && !isEditing) {
            requestAnimationFrame(() => {
                setCurrentValue(newValue);
            });
            previousValueRef.current = newValue;
        } else if (newValue !== previousValueRef.current) {
            previousValueRef.current = newValue;
        }
    }, [value, isEditing]);

    const containerStyle: React.CSSProperties = {};
    if (multiline && height !== 'auto') {
        containerStyle.minHeight = height;
    }

    const displayValue = value ? String(value) : '-';

    return (
        <div className={`${styles.fieldContainer} ${multiline ? styles.multilineContainer : ''}`} style={containerStyle}>
            <label className={styles.label}>{label}</label>

            {isEditing ? (
                <div className={styles.inputWrapper}>
                    {multiline ? (
                        <textarea
                            ref={textareaRef}
                            className={`${styles.input} ${styles.textarea} ${forceEdit ? styles.forcedInput : ''}`}
                            value={currentValue}
                            onChange={handleChange}
                            onBlur={handleBlur}
                            rows={1}
                        />
                    ) : (
                        <input
                            ref={inputRef}
                            className={`${styles.input} ${forceEdit ? styles.forcedInput : ''}`}
                            value={currentValue}
                            onChange={handleChange}
                            onBlur={handleBlur}
                            onKeyDown={handleKeyDown}
                        />
                    )}
                </div>

            ) : (
                <div
                    className={`${styles.valueDisplay} ${value ? styles.hasValue : ''} ${multiline ? styles.multilineDisplay : ''}`}
                    onClick={handleClick}
                >
                    <span className={`${styles.valueText} ${multiline ? styles.multilineText : ''}`}>
                        {displayValue}
                    </span>
                    {value && <Pencil size={12} className={styles.editIcon} />}
                </div>
            )}
        </div>
    );
};

export default EditableField;
