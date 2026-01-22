import { useState, useEffect, useRef } from "react";
import { Pencil } from "lucide-react";

interface EditableFieldProps {
  label: string;
  value: string | number | null | undefined;
  onSave: (value: string) => void;
  forceEdit?: boolean;
  multiline?: boolean;
  height?: string;
}

const EditableField = ({
  label,
  value,
  onSave,
  forceEdit = false,
  multiline = false,
  height = "auto",
}: EditableFieldProps) => {
  // Local editing state for non-forced mode
  const [localEditing, setLocalEditing] = useState(false);
  // When forceEdit is true, use it; otherwise use local state
  const isEditing = forceEdit || localEditing;
  const [currentValue, setCurrentValue] = useState(String(value || ""));
  const inputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const previousValueRef = useRef<string>(String(value || ""));

  const adjustTextareaHeight = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = el.scrollHeight + "px";
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

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
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
    if (e.key === "Enter" && !multiline) {
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
    const newValue = String(value || "");
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
  if (multiline && height !== "auto") {
    containerStyle.minHeight = height;
  }

  const displayValue = value ? String(value) : "-";

  return (
    <div
      className={`
      flex flex-col gap-[0.15rem] w-full
      ${multiline ? "min-h-[40px]" : ""}
    `}
      style={containerStyle}
    >
      <label
        className="
        text-[0.55rem]
        uppercase
        text-(--text-secondary)
        font-medium
        tracking-[0.02em]
        pl-[0.2rem]
      "
      >
        {label}
      </label>

      {isEditing ? (
        <div className="w-full flex flex-1">
          {multiline ? (
            <textarea
              ref={textareaRef}
              value={currentValue}
              onChange={handleChange}
              onBlur={handleBlur}
              rows={1}
              className={`
              w-full
              p-[0.4rem]
              rounded
              bg-[rgba(37,99,235,0.15)]
              border border-(--accent-blue)
              text-(--text-primary)
              text-[0.75rem]
              font-inherit
              outline-none
              resize-none
              overflow-hidden
              min-h-[40px]
              leading-[1.4]
              ${forceEdit ? "border-solid" : ""}
            `}
            />
          ) : (
            <input
              ref={inputRef}
              value={currentValue}
              onChange={handleChange}
              onBlur={handleBlur}
              onKeyDown={handleKeyDown}
              className={`
              w-full
              px-[0.2rem] py-[0.3rem]
              rounded
              bg-[rgba(37,99,235,0.15)]
              border border-(--accent-blue)
              text-(--text-primary)
              text-[0.8rem]
              font-inherit
              outline-none
              ${forceEdit ? "border-solid" : ""}
            `}
            />
          )}
        </div>
      ) : (
        <div
          onClick={handleClick}
          className={`
          group
          flex items-center justify-between
          px-[0.2rem] py-[0.3rem]
          rounded
          bg-transparent
          border border-transparent
          transition-all duration-200 ease
          cursor-pointer
          min-h-[1.8rem]
          ${value ? "hover:bg-white/5 hover:border-(--card-border)" : ""}
          ${
            multiline
              ? "items-start flex-1 overflow-visible rounded-md p-[0.4rem] whitespace-pre-wrap"
              : ""
          }
        `}
        >
          <span
            className={`
            text-(--text-primary)
            font-medium
            overflow-hidden
            text-ellipsis
            pl-0
            ${
              multiline
                ? "whitespace-pre-wrap overflow-visible text-[0.75rem] leading-[1.4] w-full"
                : "whitespace-nowrap text-[0.8rem]"
            }
          `}
          >
            {displayValue}
          </span>

          {value && (
            <Pencil
              size={12}
              className="
              text-(--text-secondary)
              opacity-0
              transition-opacity duration-200 ease
              flex-shrink-0
              ml-2
              group-hover:opacity-100
            "
            />
          )}
        </div>
      )}
    </div>
  );
};

export default EditableField;
