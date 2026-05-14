def get_code():
    return '''
    def capture_and_recognize_participants(self) -> list:
        \"\"\"
        Capture faces from camera and recognize people.
        Returns: list of participants
        \"\"\"
        logger.info("\\n" + "=" * 80)
        logger.info("FACE RECOGNITION (PARTICIPANTS)")
        logger.info("=" * 80)
        
        if not self.camera.open(): return []
        captured_image_path = None
        while True:
            success, frame = self.camera.read_frame()
            if not success: break
            detections = self.detector.detect_faces(frame)
            display_frame = frame.copy()
            for i, d in enumerate(detections):
                x, y, w, h = d['box']
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0,255,0), 2)
            cv2.imshow("Face Capture", display_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('c'):
                captured_image_path = str(self.images_dir / f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                cv2.imwrite(captured_image_path, frame)
                break
            elif key == ord('q'): break
        cv2.destroyAllWindows()
        
        if not captured_image_path: return []
        
        faces_data = self.detector.detect_and_extract_all_faces(captured_image_path)
        participants = []
        for i, (face_img, detection_info) in enumerate(faces_data):
            embedding = self.embedder.generate_embedding(face_img)
            if embedding is None: continue
            best_match_name, similarity, _ = self.recognizer.find_best_match(embedding)
            
            if best_match_name and similarity >= opencv_config.RECOGNITION_THRESHOLD:
                p_rec = self.database.get_person_by_name(best_match_name)
                participants.append({"id": str(p_rec['_id']), "name": best_match_name, "image": captured_image_path, "is_new": False})
            else:
                cv2.imshow("New", face_img)
                cv2.waitKey(100)
                name = input("Enter name: ").strip()
                cv2.destroyAllWindows()
                if name and self.database.store_embedding(name, embedding, False):
                    p_rec = self.database.get_person_by_name(name)
                    participants.append({"id": str(p_rec['_id']), "name": name, "image": captured_image_path, "is_new": True})
        return participants

    def display_participants_info(self, participants: list):
        for p in participants:
            print(f"\\n--- {p['name']} ---")
            if not p['is_new']:
                lm = self.database.get_last_meeting(p['id'])
                if lm: print(f"Last Meeting:\\n{lm['summary']}")

'''

with open('d:/miniproject/meeting_pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
text = re.sub(r'    def record_and_process_meeting', get_code() + '    def record_and_process_meeting', text)

with open('d:/miniproject/meeting_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(text)
