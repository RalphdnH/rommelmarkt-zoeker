"""Decoder for Cloudflare email protection obfuscation."""

from typing import Optional


def decode_cloudflare_email(encoded_string: str) -> Optional[str]:
    """
    Decode Cloudflare's email protection encoding.

    Cloudflare uses a simple XOR cipher where:
    - First 2 hex chars are the key
    - Remaining hex pairs are XORed with the key to get ASCII values

    Args:
        encoded_string: Hex-encoded string from Cloudflare protection.

    Returns:
        Decoded email address, or None if decoding fails.

    Example:
        # From URL: /cdn-cgi/l/email-protection#1234567890abcdef
        # The hex string after # is passed to this function
        email = decode_cloudflare_email("1234567890abcdef")
    """
    if not encoded_string:
        return None

    try:
        # First byte is the XOR key
        key = int(encoded_string[:2], 16)

        # Decode remaining bytes by XORing with the key
        decoded_chars = []
        for i in range(2, len(encoded_string), 2):
            hex_pair = encoded_string[i:i + 2]
            char_code = int(hex_pair, 16) ^ key
            decoded_chars.append(chr(char_code))

        return ''.join(decoded_chars)

    except (ValueError, IndexError):
        return None
