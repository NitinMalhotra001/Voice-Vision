import streamlit as st
import whisper
from io import BytesIO
import os
import numpy as np
import librosa
import librosa.display
import time
import re
from pydub import AudioSegment
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.cluster import KMeans
import tempfile
import json
import soundfile as sf


def main():
    # Add custom CSS to ensure text visibility
    st.markdown("""
    <style>
        .stApp {
            background-color: #f8f8f8;
        }
        .stMarkdown, .stText, .stSubheader, .stHeader, .stLabel, p, div, span {
            color: #111111 !important;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #232f3e !important;
        }
        .header {
            font-size: 2.5rem;
            font-weight: 700;
            color: #232f3e !important;
            margin-bottom: 1.5rem;
        }
        .stTextArea textarea {
            color: #111111 !important;
            background-color: #ffffff !important;
        }
        .stButton button {
            background-color: #FFD814;
            color: #111111;
            font-weight: 500;
        }
        .stButton button:hover {
            background-color: #F7CA00;
        }
        .upload-box {
            background-color: #e7f3ff;
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            border-left: 4px solid #2196f3;
        }
    </style>
    """, unsafe_allow_html=True)

    # Load Whisper model once
    @st.cache_resource
    def load_model(model_size="tiny"):
        """Load Whisper model with size parameter"""
        return whisper.load_model(model_size)

    # Model selector
    model_options = ["tiny", "base", "auto"]
    selected_model = st.selectbox(
        "Whisper Model (tiny recommended for low memory)",
        model_options,
        index=0,
        help="tiny: Fast/Low memory, base: Better accuracy/higher memory"
    )
    model = load_model(selected_model)

    # Language mapping
    lang_map = {
        "en": "English", "hi": "Hindi", "fr": "French", "de": "German",
        "es": "Spanish", "it": "Italian", "zh": "Chinese", "ja": "Japanese",
        "ko": "Korean", "ar": "Arabic", "ru": "Russian", "te": "Telugu",
        "ta": "Tamil", "bn": "Bengali", "pa": "Punjabi", "gu": "Gujarati", "kn": "Kannada"
    }

    def transcribe_audio(audio_bytes):
        """Transcribe audio using Whisper"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_bytes)
            
            result = model.transcribe(temp_path)
            lang_code = result['language']
            lang_name = lang_map.get(lang_code, lang_code)
            
            os.unlink(temp_path)
            
            return result["text"], lang_name, result["segments"]
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {str(e)}")

    def analyze_gender(audio_bytes):
        """Analyze audio to predict speaker gender"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_bytes)
            
            y, sr = librosa.load(temp_path, sr=None)
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_values = pitches[magnitudes > 0]
            
            os.unlink(temp_path)
            
            if len(pitch_values) == 0:
                return "Unknown"
            
            mean_pitch = np.mean(pitch_values)
            if mean_pitch < 165:
                return "Male"
            elif mean_pitch > 180:
                return "Female"
            else:
                return "Undetermined"
        except:
            return "Unknown"

    def count_speakers(audio_bytes, segments):
        """Count number of unique speakers"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_bytes)
            
            y, sr = librosa.load(temp_path, sr=None)
            features = []
            
            for segment in segments[:10]:
                start_sample = int(segment['start'] * sr)
                end_sample = int(segment['end'] * sr)
                
                if start_sample < end_sample and end_sample <= len(y):
                    segment_audio = y[start_sample:end_sample]
                    if len(segment_audio) > 512:
                        mfccs = librosa.feature.mfcc(y=segment_audio, sr=sr, n_mfcc=13)
                        mfccs_mean = np.mean(mfccs, axis=1)
                        features.append(mfccs_mean)
            
            os.unlink(temp_path)
            
            if len(features) < 2:
                return 1
            
            features = np.array(features)
            max_speakers = min(4, len(features))
            num_speakers = 1
            
            for n_clusters in range(2, max_speakers + 1):
                if len(features) >= n_clusters:
                    kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=10)
                    kmeans.fit(features)
                    if kmeans.inertia_ < 100:
                        num_speakers = n_clusters
            
            return num_speakers
        except:
            return 1

    def format_time(seconds):
        """Format seconds to MM:SS format"""
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes:02d}:{remaining_seconds:02d}"

    def create_transcript_with_timestamps(segments):
        """Create formatted transcript with timestamps"""
        transcript = ""
        for segment in segments:
            start_time = format_time(segment['start'])
            end_time = format_time(segment['end'])
            text = segment['text'].strip()
            transcript += f"[{start_time} - {end_time}] {text}\n\n"
        return transcript

    def generate_audio_visualization(audio_bytes):
        """Generate waveform and spectrogram visualization"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_bytes)
            
            y, sr = librosa.load(temp_path, sr=None)
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
            librosa.display.waveshow(y, sr=sr, ax=ax1)
            ax1.set_title('Waveform')
            ax1.set_xlabel('')
            D = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)
            img = librosa.display.specshow(D, y_axis='log', x_axis='time', sr=sr, ax=ax2)
            ax2.set_title('Spectrogram')
            fig.colorbar(img, ax=ax2, format="%+2.0f dB")
            plt.tight_layout()
            
            os.unlink(temp_path)
            return fig
        except:
            return None

    def calculate_speech_stats(segments):
        """Calculate speech statistics"""
        if not segments:
            return {}
        
        total_duration = segments[-1]['end']
        speech_duration = sum(segment['end'] - segment['start'] for segment in segments)
        word_count = sum(len(segment['text'].split()) for segment in segments)
        
        return {
            "Total Duration": f"{format_time(total_duration)} (MM:SS)",
            "Speech Duration": f"{format_time(speech_duration)} (MM:SS)",
            "Words": word_count,
            "Words per Minute": round(word_count / (speech_duration / 60)) if speech_duration > 0 else 0,
            "Segments": len(segments)
        }

    def extract_keywords(text, num_keywords=5):
        """Extract simple keywords"""
        from collections import Counter
        stop_words = {'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 
                      'he', 'she', 'it', 'they', 'them', 'the', 'a', 'an', 'and', 'or', 'to', 'of'}
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
        word_counts = Counter(filtered_words)
        return word_counts.most_common(num_keywords)

    # Initialize session state
    if 'uploaded_audio' not in st.session_state:
        st.session_state.uploaded_audio = None
    if 'uploaded_filename' not in st.session_state:
        st.session_state.uploaded_filename = None
    if 'transcription_done' not in st.session_state:
        st.session_state.transcription_done = False
    if 'transcription_text' not in st.session_state:
        st.session_state.transcription_text = ""
    if 'language' not in st.session_state:
        st.session_state.language = ""
    if 'segments' not in st.session_state:
        st.session_state.segments = []
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = {}
    if 'speech_stats' not in st.session_state:
        st.session_state.speech_stats = {}
    if 'keywords' not in st.session_state:
        st.session_state.keywords = []
    if 'timestamped_transcript' not in st.session_state:
        st.session_state.timestamped_transcript = ""
    if 'visualization' not in st.session_state:
        st.session_state.visualization = None
    if 'processing_time' not in st.session_state:
        st.session_state.processing_time = 0

    # Main UI
    st.markdown('<div class="header">🎙️ Audio Transcription</div>', unsafe_allow_html=True)
    
    # Create columns for layout
    col1, col2 = st.columns([3, 1])

    with col1:
        # Upload Section - Step 1 (Now the only step)
        st.subheader("📁 Step 1: Upload Audio File")
        
        # File uploader for audio files
        uploaded_file = st.file_uploader(
            "Choose an audio file (MP3, WAV, M4A)",
            type=["mp3", "wav", "m4a"],
            accept_multiple_files=False,
            help="200MB per file • MP3, WAV, M4A"
        )
        
        if uploaded_file is not None:
            audio_bytes = uploaded_file.read()
            st.audio(audio_bytes, format="audio/mp3")
            st.caption(f"File name: {uploaded_file.name}")
            st.caption(f"File size: {len(audio_bytes) / 1024:.1f} KB")
            
            if st.button("✅ Use this file for transcription", type="primary", use_container_width=True):
                st.session_state.uploaded_audio = audio_bytes
                st.session_state.uploaded_filename = uploaded_file.name
                st.success(f"✅ File loaded: {uploaded_file.name}")
                st.rerun()
        
        # Show current selection
        if st.session_state.uploaded_audio:
            st.markdown("---")
            st.markdown("### 🎵 Current Audio Ready for Transcription")
            st.audio(st.session_state.uploaded_audio, format="audio/wav")
            st.info(f"**Selected file:** {st.session_state.uploaded_filename}")
            
            col_download, col_clear_all = st.columns(2)
            
            with col_download:
                st.download_button(
                    label="📥 Download Audio File",
                    data=st.session_state.uploaded_audio,
                    file_name=st.session_state.uploaded_filename,
                    mime="audio/wav",
                    use_container_width=True
                )
            
            with col_clear_all:
                if st.button("🗑️ Clear File", use_container_width=True):
                    st.session_state.uploaded_audio = None
                    st.session_state.uploaded_filename = None
                    st.session_state.transcription_done = False
                    st.rerun()
        
        # Advanced options
        with st.expander("🔧 Analysis Options", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                enable_speaker_detection = st.checkbox("Detect number of speakers", value=False)
                enable_gender_detection = st.checkbox("Detect speaker gender", value=False)
            with col_b:
                enable_visualization = st.checkbox("Generate audio visualization", value=False)
                enable_keywords = st.checkbox("Extract keywords", value=True)

        # Step 2: Transcribe Button
        st.markdown("---")
        st.subheader("🎤 Step 2: Transcribe Audio")
        
        if st.session_state.uploaded_audio:
            if st.button("🎤 TRANSCRIBE AUDIO", type="primary", use_container_width=True):
                with st.spinner("Transcribing audio... This may take a moment."):
                    try:
                        start_time = time.time()
                        
                        text, lang, segments = transcribe_audio(st.session_state.uploaded_audio)
                        
                        st.session_state.transcription_text = text
                        st.session_state.language = lang
                        st.session_state.segments = segments
                        
                        analysis_results = {}
                        speech_stats = {}
                        keywords = []
                        visualization = None
                        
                        if enable_gender_detection:
                            try:
                                gender = analyze_gender(st.session_state.uploaded_audio)
                                analysis_results["Dominant Speaker Gender"] = gender
                            except Exception as e:
                                st.warning(f"Could not detect gender: {e}")
                        
                        if enable_speaker_detection:
                            try:
                                num_speakers = count_speakers(st.session_state.uploaded_audio, segments)
                                analysis_results["Number of Speakers"] = num_speakers
                            except Exception as e:
                                st.warning(f"Could not detect speakers: {e}")
                        
                        if enable_speaker_detection or enable_gender_detection:
                            speech_stats = calculate_speech_stats(segments)
                        
                        if enable_keywords:
                            keywords = extract_keywords(text)
                        
                        if enable_visualization:
                            try:
                                visualization = generate_audio_visualization(st.session_state.uploaded_audio)
                            except Exception as e:
                                st.warning(f"Could not generate visualization: {e}")
                        
                        timestamped_transcript = create_transcript_with_timestamps(segments)
                        
                        st.session_state.analysis_results = analysis_results
                        st.session_state.speech_stats = speech_stats
                        st.session_state.keywords = keywords
                        st.session_state.timestamped_transcript = timestamped_transcript
                        st.session_state.visualization = visualization
                        st.session_state.processing_time = time.time() - start_time
                        st.session_state.transcription_done = True
                        
                        st.success(f"✅ Transcription Complete! (Processed in {st.session_state.processing_time:.2f} seconds)")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Transcription failed: {str(e)}")
                        st.info("Tips: Try a different audio file, ensure clear speech, or use a shorter clip.")
        else:
            st.info("📌 Please upload an audio file first, then click 'Transcribe Audio'")

        # Show results
        if st.session_state.transcription_done:
            st.markdown("---")
            st.markdown(f"**🗣️ Detected Language:** {st.session_state.language}")
            
            if st.session_state.analysis_results:
                st.subheader("📊 Audio Analysis")
                for key, value in st.session_state.analysis_results.items():
                    st.markdown(f"**{key}:** {value}")
            
            if st.session_state.speech_stats:
                st.subheader("📈 Speech Statistics")
                stats_df = pd.DataFrame({
                    "Metric": list(st.session_state.speech_stats.keys()),
                    "Value": list(st.session_state.speech_stats.values())
                })
                st.table(stats_df)
            
            if st.session_state.keywords:
                st.subheader("🔑 Key Topics")
                keywords_str = ", ".join([f"**{word}** ({count})" for word, count in st.session_state.keywords])
                st.markdown(keywords_str)
            
            if st.session_state.visualization:
                st.subheader("📊 Audio Visualization")
                st.pyplot(st.session_state.visualization)
            
            tab1, tab2 = st.tabs(["Plain Text", "With Timestamps"])
            
            with tab1:
                st.text_area("Transcribed Text", st.session_state.transcription_text, height=300)
                
                download_txt = BytesIO()
                download_txt.write(st.session_state.transcription_text.encode())
                download_txt.seek(0)
                st.download_button(
                    "📥 Download Text",
                    data=download_txt,
                    file_name="transcription.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with tab2:
                st.text_area("Timestamped Transcript", st.session_state.timestamped_transcript, height=400)
                
                download_timestamped = BytesIO()
                download_timestamped.write(st.session_state.timestamped_transcript.encode())
                download_timestamped.seek(0)
                st.download_button(
                    "📥 Download Timestamped",
                    data=download_timestamped,
                    file_name="timestamped_transcript.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
                json_data = {
                    "language": st.session_state.language,
                    "segments": st.session_state.segments,
                    "analysis": st.session_state.analysis_results
                }
                json_str = json.dumps(json_data, indent=2)
                st.download_button(
                    "📥 Download JSON",
                    data=json_str,
                    file_name="transcription.json",
                    mime="application/json",
                    use_container_width=True
                )

    with col2:
        st.markdown("""
        ### 📖 Quick Guide
        
        **2 Simple Steps:**
        
        **Step 1: Upload Audio**
        - Upload MP3, WAV, or M4A file
        - Click "Use this file for transcription"
        
        **Step 2: Transcribe**
        - Click **TRANSCRIBE AUDIO**
        - Download your results
        
        **Features:**
        - 🎯 Whisper AI transcription
        - 🌍 15+ languages detected
        - 👥 Speaker detection
        - 🎵 Gender voice analysis
        - 📊 Audio visualizations
        - 🔑 Keyword extraction
        
        **Supported Formats:**
        - MP3, WAV, M4A
        - Up to 200MB per file
        
        **Tips for best results:**
        - Use clear audio with minimal background noise
        - Ensure speech is clear and audible
        - Longer files take more processing time
        """)

if __name__ == "__main__":
    main()