/**
 * Kippe WMS
 *
 * Local deterministic Tailwind build.
 *
 * Runtime rule:
 *   The browser never loads Tailwind from a CDN.
 *
 * Build rule:
 *   Utilities are extracted only from Kippe-owned frontend sources.
 */
module.exports = {
    content: [
        "../../web/index.html",
        "../../web/js/**/*.js"
    ],

    theme: {
        extend: {
            colors: {
                "kippe-blue": "#124191",
                "kippe-red": "#e31c23"
            }
        }
    },

    plugins: []
};
