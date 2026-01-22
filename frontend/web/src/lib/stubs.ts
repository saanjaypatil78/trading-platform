export const cva = (base, config) => (props) => {
    // Simplified stub since we can't install packages
    const { variants, defaultVariants } = config || {};
    const classes = [base];
    // Very basic logic just to make the code not crash if compiled without the lib
    // In reality, user needs to run npm install in their environment
    return classes.join(' ');
};

export type VariantProps<T> = any;
