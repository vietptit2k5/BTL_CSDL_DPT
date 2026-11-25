-- Open this file in MySQL Workbench on the project's connection.
USE d23_nhom12;
SELECT generation_id,status,source_sha256,imported_at FROM generations ORDER BY imported_at DESC;
SET @g = (SELECT generation_id FROM generations WHERE status='ready' ORDER BY imported_at DESC LIMIT 1);

SELECT 'videos' AS table_name,COUNT(*) AS row_count FROM videos WHERE generation_id=@g
UNION ALL SELECT 'keyframes',COUNT(*) FROM keyframes WHERE generation_id=@g
UNION ALL SELECT 'frame_features',COUNT(*) FROM frame_features WHERE generation_id=@g
UNION ALL SELECT 'video_features',COUNT(*) FROM video_features WHERE generation_id=@g;

SELECT class_code,COUNT(*) AS video_count FROM videos WHERE generation_id=@g GROUP BY class_code ORDER BY class_code;
SELECT * FROM feature_catalog WHERE generation_id=@g ORDER BY feature;
SELECT * FROM v_video_overview WHERE generation_id=@g ORDER BY video_id LIMIT 100;

SELECT video_id,relative_path,
 JSON_EXTRACT(metadata_json,'$.duration') AS duration_seconds,
 JSON_EXTRACT(crop_json,'$') AS crop_box,
 JSON_EXTRACT(quality_json,'$.status') AS review_status
 FROM videos WHERE generation_id=@g ORDER BY video_id LIMIT 20;

SELECT video_id,frame_index,target_time,actual_time,image_path
 FROM keyframes WHERE generation_id=@g AND video_id='SEA005' ORDER BY frame_index;

SELECT feature,COUNT(*) AS vector_count,MIN(OCTET_LENGTH(vector)) AS min_bytes,
 MAX(OCTET_LENGTH(vector)) AS max_bytes FROM frame_features
 WHERE generation_id=@g GROUP BY feature;
SELECT feature,COUNT(*) AS vector_count,MIN(OCTET_LENGTH(vector)) AS min_bytes,
 MAX(OCTET_LENGTH(vector)) AS max_bytes FROM video_features
 WHERE generation_id=@g GROUP BY feature;
