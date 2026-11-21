
import cv2
import numpy as np


def decode_qr_image(image_bytes):
    """
    Decode QR code data from uploaded image bytes.

    Returns:
        Decoded QR text if found.
        None if no QR code is detected.
    """

    try:
        # Convert image bytes into NumPy array
        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8
        )

        # Convert array into OpenCV image
        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        # Check image validity
        if image is None:
            raise ValueError("Invalid image file.")

        # Create QR code detector
        detector = cv2.QRCodeDetector()

        # Detect and decode QR code
        decoded_data, points, _ = detector.detectAndDecode(image)

        # Return decoded data
        if decoded_data:
            return decoded_data

        return None

    except ValueError:
        raise

    except Exception as e:
        raise ValueError(
            f"QR decoding failed: {str(e)}"
        )
