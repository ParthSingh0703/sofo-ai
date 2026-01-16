/**
 * Utility functions for formatting canonical JSON values for display
 */

export const formatCurrency = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return '-';
    if (value >= 1000000) {
        return `$${(value / 1000000).toFixed(2)}M`;
    }
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value);
};

export const formatDate = (value: string | null | undefined): string => {
    if (!value) return '-';
    try {
        const date = new Date(value);
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const year = date.getFullYear();
        return `${month}/${day}/${year}`;
    } catch {
        return value;
    }
};

export const formatArray = (value: string[] | null | undefined): string => {
    if (!value || !Array.isArray(value) || value.length === 0) return '-';
    return value.join(', ');
};

export const formatBoolean = (value: boolean | null | undefined): string => {
    if (value === null || value === undefined) return '-';
    return value ? 'Yes' : 'No';
};

export const formatPercentage = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return '-';
    return `${value.toFixed(2)}%`;
};

export const formatNumber = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return '-';
    return String(value);
};

export const formatDecimal = (value: number | null | undefined, decimals: number = 2): string => {
    if (value === null || value === undefined) return '-';
    return value.toFixed(decimals);
};

/**
 * Extract value from canonical JSON using path array
 */
export const getCanonicalValue = (
    canonical: Record<string, unknown>,
    path: string[]
): unknown => {
    let current: unknown = canonical;
    for (const key of path) {
        if (current && typeof current === 'object' && key in current) {
            current = (current as Record<string, unknown>)[key];
        } else {
            return null;
        }
    }
    return current;
};

/**
 * Set value in canonical JSON using path array
 */
export const setCanonicalValue = (
    canonical: Record<string, unknown>,
    path: string[],
    value: unknown
): void => {
    let current: Record<string, unknown> = canonical;
    for (let i = 0; i < path.length - 1; i++) {
        const key = path[i];
        if (!(key in current) || typeof current[key] !== 'object' || current[key] === null) {
            current[key] = {};
        }
        current = current[key] as Record<string, unknown>;
    }
    current[path[path.length - 1]] = value;
};

/**
 * Calculate total bedrooms from main_level_bedrooms + other_level_bedrooms
 */
export const calculateTotalBedrooms = (
    canonical: Record<string, unknown>
): number | null => {
    const property = canonical.property as Record<string, unknown> | undefined;
    if (!property) return null;
    const main = (property.main_level_bedrooms as number) || 0;
    const other = (property.other_level_bedrooms as number) || 0;
    const total = main + other;
    return total > 0 ? total : null;
};

/**
 * Calculate total bathrooms from bathrooms_full + bathrooms_half
 */
export const calculateTotalBathrooms = (
    canonical: Record<string, unknown>
): string | null => {
    const property = canonical.property as Record<string, unknown> | undefined;
    if (!property) return null;
    const full = (property.bathrooms_full as number) || 0;
    const half = (property.bathrooms_half as number) || 0;
    if (full === 0 && half === 0) return null;
    if (half === 0) return String(full);
    return `${full}.${half}`;
};
