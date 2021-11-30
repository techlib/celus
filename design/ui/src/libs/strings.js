/**
 * Generate a pseudo-random string of digits and lower-case letters.
 * Math.random().toString(36) produces a string starting with "0.",
 * as Math.randow returns a float between 0 * and 1 (excluded).
 * Conversion in base 36 produces a string of usually 12 to 13 chars,
 * depending on the input.
 * @param {number} [length] - Desired length. Max 10-11 characters.
 * @returns {string}
 */
export function randomString(length = 10) {
	return Math.random().toString(36).substring(2, length + 2);
}
