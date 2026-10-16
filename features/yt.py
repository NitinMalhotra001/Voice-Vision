import streamlit as st
import os
import re
import tempfile
import time
from collections import Counter
import nltk
import yt_dlp
import whisper
import numpy as np

# Download nltk data
try:
    nltk.data.find("tokenizers/punkt")
except Exception:
    nltk.download("punkt", quiet=True)

def main():
    # Force text visibility
    st.markdown("""
    <style>
        * {
            color: #111111 !important;
        }
        .stApp {
            background-color: #ffffff !important;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #232f3e !important;
        }
        .stButton button {
            background-color: #FFD814 !important;
            color: #111111 !important;
            font-weight: 500 !important;
        }
        .stTextArea textarea {
            color: #111111 !important;
            background-color: #ffffff !important;
            border: 1px solid #ddd !important;
        }
        .stAlert {
            background-color: #e7f3ff !important;
        }
        .stAlert p, .stAlert div {
            color: #111111 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<h2 style="color: #232f3e; font-size: 1.8rem;">🎬 YouTube Audio Transcriber</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color: #555555;">Extract text by listening to video audio - no captions needed!</p>', unsafe_allow_html=True)

    with st.expander("ℹ️ How to use", expanded=False):
        st.markdown("""
        **Instructions:**
        1. Enter a YouTube video URL
        2. Select Whisper model (tiny is fastest)
        3. Click **Download & Transcribe**
        4. View transcription line by line
        
        **How it works:**
        - Downloads audio from YouTube video
        - Uses Whisper AI to transcribe speech
        - Shows output line by line with timestamps
        
        **Note:** 
        - First download may take a few seconds
        - Longer videos take more time to process
        - Works with any YouTube video (even without captions!)
        """)

    # Model selection
    model_options = ["tiny", "base", "small", "medium"]
    selected_model = st.selectbox(
        "Whisper Model (tiny = fastest, medium = most accurate)",
        model_options,
        index=0,
        help="Tiny is recommended for quick results"
    )

    @st.cache_resource
    def load_whisper_model(model_size):
        """Load Whisper model"""
        return whisper.load_model(model_size)

    # Load model
    with st.spinner(f"Loading {selected_model} model... First time may take a moment"):
        model = load_whisper_model(selected_model)

    # URL input
    video_url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        key="youtube_url_input"
    )

    # Progress indicators
    download_status = st.empty()
    transcribe_status = st.empty()

    def download_audio(youtube_url, output_path):
        """Download audio from YouTube video"""
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            title = info.get('title', 'audio')
            duration = info.get('duration', 0)
            audio_file = os.path.join(output_path, f"{title}.mp3")
            return audio_file, title, duration

    def transcribe_audio_file(audio_path, model, progress_callback=None):
        """Transcribe audio file line by line"""
        result = model.transcribe(audio_path)
        
        # Format output line by line
        segments = []
        for segment in result["segments"]:
            start_time = format_time(segment["start"])
            end_time = format_time(segment["end"])
            text = segment["text"].strip()
            segments.append({
                "start": start_time,
                "end": end_time,
                "text": text,
                "start_seconds": segment["start"],
                "end_seconds": segment["end"]
            })
        
        return segments, result["text"], result["language"]

    def format_time(seconds):
        """Format seconds to HH:MM:SS or MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    # Language mapping
    lang_map = {
        "en": "English", "hi": "Hindi", "fr": "French", "de": "German",
        "es": "Spanish", "it": "Italian", "zh": "Chinese", "ja": "Japanese",
        "ko": "Korean", "ar": "Arabic", "ru": "Russian", "te": "Telugu",
        "ta": "Tamil", "bn": "Bengali", "pa": "Punjabi", "gu": "Gujarati"
    }

    # Analyze button
    if st.button("🎤 Download & Transcribe", type="primary", use_container_width=True):
        if not video_url:
            st.warning("⚠️ Please enter a YouTube URL")
            return

        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Step 1: Download audio
                download_status.info("📥 Downloading audio from YouTube... This may take a moment")
                
                audio_file, video_title, duration = download_audio(video_url, temp_dir)
                
                if not os.path.exists(audio_file):
                    st.error("Failed to download audio")
                    return
                
                # Format duration
                dur_min = duration // 60
                dur_sec = duration % 60
                download_status.success(f"✅ Audio downloaded! Duration: {dur_min}m {dur_sec}s | Title: {video_title[:50]}...")
                
                # Step 2: Transcribe
                transcribe_status.info("🎙️ Transcribing audio with Whisper AI... This may take a moment")
                
                segments, full_text, detected_lang = transcribe_audio_file(audio_file, model)
                
                lang_name = lang_map.get(detected_lang, detected_lang)
                transcribe_status.success(f"✅ Transcription complete! Detected language: {lang_name}")
                
                # Display video info
                st.subheader("📹 Video Information")
                col1, col2 = st.columns(2)
                with col1:
                    thumbnail_url = f"https://img.youtube.com/vi/{extract_video_id(video_url)}/mqdefault.jpg"
                    st.image(thumbnail_url, use_container_width=True)
                with col2:
                    st.markdown(f"**Title:** {video_title}")
                    st.markdown(f"**Duration:** {dur_min}m {dur_sec}s")
                    st.markdown(f"**Detected Language:** {lang_name}")
                    st.markdown(f"**Segments:** {len(segments)}")
                    st.markdown(f"**Total Words:** {len(full_text.split())}")
                
                # Display transcription line by line
                st.subheader("📝 Transcription (Line by Line)")
                
                # Create a container for line-by-line display
                transcript_container = st.container()
                
                with transcript_container:
                    for i, segment in enumerate(segments):
                        # Create a visual separator for each line
                        st.markdown(f"""
                        <div style="
                            background-color: #f8f9fa;
                            padding: 8px 12px;
                            margin: 5px 0;
                            border-radius: 5px;
                            border-left: 3px solid #FFD814;
                        ">
                            <span style="font-family: monospace; color: #666; font-size: 0.8rem;">[{segment['start']} - {segment['end']}]</span>
                            <span style="color: #111; font-size: 1rem;"> {segment['text']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Also provide a text area for copying
                with st.expander("📋 View as plain text"):
                    plain_text = "\n".join([f"[{s['start']} - {s['end']}] {s['text']}" for s in segments])
                    st.text_area("Full Transcript", plain_text, height=300)
                
                # Word statistics
                with st.expander("📊 Word Statistics"):
                    words = [word.lower() for word in nltk.word_tokenize(full_text) if word.isalpha() and len(word) > 3]
                    if words:
                        common_words = Counter(words).most_common(15)
                        st.write("**Most common words:**")
                        for word, count in common_words:
                            st.write(f"• **{word}** : {count} times")
                
                # Download options
                st.subheader("📥 Download Options")
                
                col_d1, col_d2, col_d3 = st.columns(3)
                
                with col_d1:
                    # Download full transcript as TXT
                    transcript_txt = "\n".join([f"[{s['start']} - {s['end']}] {s['text']}" for s in segments])
                    st.download_button(
                        label="📄 Download Transcript (TXT)",
                        data=transcript_txt.encode("utf-8"),
                        file_name=f"{sanitize_filename(video_title)}_transcript.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with col_d2:
                    # Download as SRT (subtitle format)
                    srt_content = generate_srt(segments)
                    st.download_button(
                        label="🎬 Download as SRT",
                        data=srt_content.encode("utf-8"),
                        file_name=f"{sanitize_filename(video_title)}.srt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with col_d3:
                    # Download plain text (no timestamps)
                    st.download_button(
                        label="📝 Download Plain Text",
                        data=full_text.encode("utf-8"),
                        file_name=f"{sanitize_filename(video_title)}_text.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                # Cleanup
                download_status.empty()
                transcribe_status.empty()
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.info("Please make sure the URL is valid and you have ffmpeg installed")
                download_status.empty()
                transcribe_status.empty()

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r'v=([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'shorts/([a-zA-Z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""

def sanitize_filename(filename):
    """Sanitize filename"""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)[:50]

def generate_srt(segments):
    """Generate SRT subtitle format"""
    srt_content = ""
    for i, seg in enumerate(segments, 1):
        # Convert to SRT time format (HH:MM:SS,mmm)
        start_seconds = seg.get("start_seconds", 0)
        end_seconds = seg.get("end_seconds", 0)
        
        start_srt = format_srt_time(start_seconds)
        end_srt = format_srt_time(end_seconds)
        
        srt_content += f"{i}\n"
        srt_content += f"{start_srt} --> {end_srt}\n"
        srt_content += f"{seg['text']}\n\n"
    
    return srt_content

def format_srt_time(seconds):
    """Format seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

if __name__ == "__main__":
    main()