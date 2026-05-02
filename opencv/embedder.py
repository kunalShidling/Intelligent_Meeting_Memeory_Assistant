"""
Face embedding module using FaceNet.
Generates 512-dimensional embeddings from face images.
"""

import cv2
import numpy as np
from PIL import Image
import torch
from facenet_pytorch import InceptionResnetV1
from typing import Optional, Tuple
import logging
import config

# Configure logging
logger = logging.getLogger(__name__)


class FaceEmbedder:
    """Face embedder using pretrained FaceNet."""
    
    def __init__(self):
        """Initialize FaceNet model."""
        try:
            # Load pretrained FaceNet model (trained on VGGFace2)
            self.device = torch.device(config.FACENET_DEVICE)
            self.model = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
            
            logger.info(f"FaceNet model loaded successfully on device: {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to initialize FaceNet: {e}")
            raise
    
    def preprocess_face(self, face_image: np.ndarray) -> torch.Tensor:
        """
        Preprocess face image for FaceNet.
        
        Steps:
        1. Convert BGR to RGB
        2. Resize to 160x160
        3. Normalize pixel values
        4. Convert to tensor
        
        Args:
            face_image: Face image in BGR format (from OpenCV)
            
        Returns:
            torch.Tensor: Preprocessed face tensor ready for FaceNet
        """
        try:
            # Convert BGR to RGB
            rgb_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
            logger.debug(f"Converted BGR to RGB - Shape: {rgb_face.shape}")
            
            # Resize to 160x160 (FaceNet input size)
            resized = cv2.resize(rgb_face, (config.FACENET_INPUT_SIZE, config.FACENET_INPUT_SIZE))
            logger.debug(f"Resized to {config.FACENET_INPUT_SIZE}x{config.FACENET_INPUT_SIZE}")
            
            # Convert to PIL Image for compatibility
            pil_image = Image.fromarray(resized)
            
            # Convert to tensor and normalize
            # FaceNet expects pixels in range [0, 255], we'll normalize to [-1, 1]
            image_tensor = torch.from_numpy(np.array(pil_image)).float()
            
            # Normalize: (pixel - mean) / std
            # For FaceNet: mean=127.5, std=128.0 to get range [-1, 1]
            normalized = (image_tensor - config.PIXEL_MEAN) / config.PIXEL_STD
            
            # Rearrange from HWC to CHW (Height, Width, Channels -> Channels, Height, Width)
            normalized = normalized.permute(2, 0, 1)
            
            # Add batch dimension
            normalized = normalized.unsqueeze(0)
            
            logger.debug(f"Preprocessed tensor shape: {normalized.shape}")
            
            return normalized.to(self.device)
            
        except Exception as e:
            logger.error(f"Error preprocessing face: {e}")
            raise
    
    def generate_embedding(self, face_image: np.ndarray) -> np.ndarray:
        """
        Generate face embedding using FaceNet.
        
        Args:
            face_image: Face image as numpy array (BGR format from OpenCV)
            
        Returns:
            np.ndarray: 512-dimensional L2-normalized embedding
        """
        try:
            # Preprocess the face image
            face_tensor = self.preprocess_face(face_image)
            
            with torch.no_grad():
                # Generate embedding
                embedding = self.model(face_tensor)
                
                # Convert to numpy
                embedding_np = embedding.cpu().numpy().flatten()
                
                # L2 normalization
                norm = np.linalg.norm(embedding_np)
                if norm > 0:
                    embedding_normalized = embedding_np / norm
                else:
                    logger.warning("Zero norm embedding - cannot normalize")
                    embedding_normalized = embedding_np
                
                logger.debug(f"Generated embedding - Shape: {embedding_normalized.shape}")
                
                return embedding_normalized
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def log_embedding_stats(self, embedding: np.ndarray):
        """
        Log statistics about the embedding.
        
        Args:
            embedding: Face embedding vector
        """
        try:
            mean = np.mean(embedding)
            std = np.std(embedding)
            l2_norm = np.linalg.norm(embedding)
            first_5 = embedding[:5]
            
            logger.info("=" * 60)
            logger.info("EMBEDDING STATISTICS:")
            logger.info(f"  Shape:        {embedding.shape}")
            logger.info(f"  Mean:         {mean:.6f}")
            logger.info(f"  Std Dev:      {std:.6f}")
            logger.info(f"  L2 Norm:      {l2_norm:.6f}")
            logger.info(f"  First 5 vals: {first_5}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error logging embedding stats: {e}")
    
    def compute_embedding_checksum(self, embedding: np.ndarray) -> str:
        """
        Compute checksum of embedding for duplicate detection.
        
        Args:
            embedding: Face embedding vector
            
        Returns:
            str: Hex digest of embedding
        """
        import hashlib
        
        # Convert to bytes and compute hash
        embedding_bytes = embedding.tobytes()
        checksum = hashlib.md5(embedding_bytes).hexdigest()
        
        logger.debug(f"Embedding checksum: {checksum}")
        return checksum
    
    def embed_face(self, face_image: np.ndarray) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Generate embedding from face image.
        
        Args:
            face_image: Face image in BGR format
            
        Returns:
            Tuple[bool, Optional[np.ndarray]]: (success, embedding)
        """
        try:
            logger.info(f"Generating embedding for face - Shape: {face_image.shape}")
            
            # Generate embedding
            embedding = self.generate_embedding(face_image)
            
            # Validate embedding size
            if len(embedding) != config.EMBEDDING_SIZE:
                logger.error(
                    f"Invalid embedding size: {len(embedding)}, "
                    f"expected {config.EMBEDDING_SIZE}"
                )
                return False, None
            
            # Log statistics
            self.log_embedding_stats(embedding)
            
            logger.info("Embedding generated successfully")
            return True, embedding
            
        except Exception as e:
            logger.error(f"Error in embed_face: {e}")
            return False, None
    
    def embed_from_file(self, image_path: str) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Generate embedding from image file.
        
        Args:
            image_path: Path to face image
            
        Returns:
            Tuple[bool, Optional[np.ndarray]]: (success, embedding)
        """
        try:
            # Read image
            face_image = cv2.imread(image_path)
            if face_image is None:
                logger.error(f"Failed to read image: {image_path}")
                return False, None
            
            return self.embed_face(face_image)
            
        except Exception as e:
            logger.error(f"Error in embed_from_file: {e}")
            return False, None
    
    def compare_embeddings(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Compare two embeddings using cosine similarity.
        
        Args:
            emb1: First embedding
            emb2: Second embedding
            
        Returns:
            float: Cosine similarity (0 to 1)
        """
        try:
            # Compute cosine similarity
            # Since embeddings are L2-normalized, dot product = cosine similarity
            similarity = np.dot(emb1, emb2)
            
            # Clip to [0, 1] range (should already be in [-1, 1])
            similarity = np.clip(similarity, -1.0, 1.0)
            
            # Convert to [0, 1] range for easier interpretation
            # similarity = (similarity + 1.0) / 2.0
            
            logger.debug(f"Cosine similarity: {similarity:.4f}")
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error comparing embeddings: {e}")
            return 0.0


def main():
    """Test face embedder."""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT
    )
    
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python embedder.py <face_image_path> [face_image_path_2]")
        return
    
    embedder = FaceEmbedder()
    
    # Generate embedding for first image
    image1_path = sys.argv[1]
    success1, emb1 = embedder.embed_from_file(image1_path)
    
    if success1:
        print(f"\nEmbedding generated for: {image1_path}")
        print(f"Shape: {emb1.shape}")
        print(f"First 10 values: {emb1[:10]}")
        
        # If second image provided, compare
        if len(sys.argv) >= 3:
            image2_path = sys.argv[2]
            success2, emb2 = embedder.embed_from_file(image2_path)
            
            if success2:
                similarity = embedder.compare_embeddings(emb1, emb2)
                print(f"\nSimilarity between images: {similarity:.4f}")
                
                if similarity >= config.RECOGNITION_THRESHOLD:
                    print("✓ Same person (likely)")
                else:
                    print("✗ Different persons (likely)")
    else:
        print("Failed to generate embedding")


if __name__ == "__main__":
    main()
