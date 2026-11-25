-- Installed by: python run.py --config var/admin.config.json mysql setup
USE d23_nhom12;
SET @g=(SELECT generation_id FROM generations WHERE status='ready' ORDER BY imported_at DESC LIMIT 1);
SELECT video_id,class_code,duration_seconds,fps,width,height,codec FROM v_video_metadata WHERE generation_id=@g ORDER BY video_id;
SELECT video_id,duration_seconds FROM v_video_metadata WHERE generation_id=@g AND class_code='WAT' AND duration_seconds<=10 ORDER BY duration_seconds;
SELECT video_id,width,height FROM v_video_metadata WHERE generation_id=@g AND height>width;
SELECT class_code,COUNT(*) AS videos,AVG(duration_seconds) AS mean_duration,SUM(size_bytes) AS total_bytes FROM v_video_metadata WHERE generation_id=@g GROUP BY class_code;
