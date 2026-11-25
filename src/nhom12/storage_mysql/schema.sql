CREATE TABLE schema_metadata (
  id TINYINT PRIMARY KEY CHECK (id=1), version VARCHAR(32) NOT NULL
) ENGINE=InnoDB;
INSERT INTO schema_metadata VALUES (1,'nhom12-mysql-v1');
CREATE TABLE generations (
  generation_id CHAR(32) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  status VARCHAR(16) NOT NULL CHECK (status IN ('importing','ready','failed')),
  source_sha256 CHAR(64) NOT NULL,
  context_json JSON NOT NULL,
  imported_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB;
CREATE TABLE feature_catalog (
  generation_id CHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  feature VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  dimension INT NOT NULL, normalization VARCHAR(32) NOT NULL, distance VARCHAR(32) NOT NULL,
  PRIMARY KEY (generation_id,feature),
  FOREIGN KEY (generation_id) REFERENCES generations(generation_id)
) ENGINE=InnoDB;
CREATE TABLE videos (
  generation_id CHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  video_id VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  class_code VARCHAR(3) NOT NULL,
  relative_path VARCHAR(255) NOT NULL, sha256 CHAR(64) NOT NULL, size_bytes BIGINT UNSIGNED NOT NULL,
  metadata_json JSON NOT NULL, crop_json JSON NOT NULL, quality_json JSON NOT NULL,
  PRIMARY KEY (generation_id,video_id), UNIQUE (generation_id,relative_path),
  FOREIGN KEY (generation_id) REFERENCES generations(generation_id)
) ENGINE=InnoDB;
CREATE TABLE keyframes (
  generation_id CHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  video_id VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  frame_index INT NOT NULL CHECK (frame_index BETWEEN 0 AND 15),
  target_time DOUBLE NOT NULL CHECK (target_time>=0), actual_time DOUBLE NOT NULL CHECK (actual_time>=0),
  image_path TEXT NOT NULL,
  PRIMARY KEY (generation_id,video_id,frame_index),
  FOREIGN KEY (generation_id,video_id) REFERENCES videos(generation_id,video_id)
) ENGINE=InnoDB;
CREATE TABLE frame_features (
  generation_id CHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  video_id VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  frame_index INT NOT NULL,
  feature VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  vector BLOB NOT NULL,
  PRIMARY KEY (generation_id,video_id,frame_index,feature),
  FOREIGN KEY (generation_id,video_id,frame_index) REFERENCES keyframes(generation_id,video_id,frame_index),
  FOREIGN KEY (generation_id,feature) REFERENCES feature_catalog(generation_id,feature),
  CHECK ((feature='hsv' AND OCTET_LENGTH(vector)=512) OR
         (feature='lbp' AND OCTET_LENGTH(vector)=40) OR
         (feature='clip' AND OCTET_LENGTH(vector)=2048))
) ENGINE=InnoDB;
CREATE TABLE video_features (
  generation_id CHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  video_id VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  feature VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  vector BLOB NOT NULL,
  PRIMARY KEY (generation_id,video_id,feature),
  FOREIGN KEY (generation_id,video_id) REFERENCES videos(generation_id,video_id),
  FOREIGN KEY (generation_id,feature) REFERENCES feature_catalog(generation_id,feature),
  CHECK (feature='motion' AND OCTET_LENGTH(vector)=96)
) ENGINE=InnoDB;
CREATE TABLE video_artifacts (
  generation_id CHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  video_id VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  manifest_json JSON NOT NULL,
  PRIMARY KEY (generation_id,video_id),
  FOREIGN KEY (generation_id,video_id) REFERENCES videos(generation_id,video_id)
) ENGINE=InnoDB;
CREATE VIEW v_video_overview AS
 SELECT v.generation_id,v.video_id,v.class_code,v.relative_path,v.size_bytes,
 JSON_UNQUOTE(JSON_EXTRACT(v.quality_json,'$.status')) AS quality_status,
 COUNT(k.frame_index) AS keyframe_count
 FROM videos v LEFT JOIN keyframes k ON k.generation_id=v.generation_id AND k.video_id=v.video_id
 GROUP BY v.generation_id,v.video_id,v.class_code,v.relative_path,v.size_bytes,v.quality_json;
