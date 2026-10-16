import streamlit as st
import time
import os
import tempfile
from googletrans import Translator
from io import BytesIO
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder


def main():
    # Force ALL text to be visible with high-priority CSS
    st.markdown("""
    <style>
        /* Force ALL elements to have dark text */
        * {
            color: #111111 !important;
        }
        
        .stApp {
            background-color: #ffffff !important;
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6, .st-emotion-cache-1v0mbdj h1 {
            color: #232f3e !important;
        }
        
        /* Selectbox - CRITICAL for language visibility */
        .stSelectbox label, 
        .stSelectbox div, 
        .stSelectbox span,
        .stSelectbox [data-baseweb="select"] span,
        .stSelectbox [data-baseweb="select"] div,
        .st-emotion-cache-1y4p8pa,
        .st-emotion-cache-1whautp {
            color: #111111 !important;
            background-color: #ffffff !important;
        }
        
        /* Selectbox dropdown options */
        div[role="listbox"] div,
        div[role="option"],
        .st-emotion-cache-1n76uvr {
            color: #111111 !important;
            background-color: #ffffff !important;
        }
        
        /* Selectbox input field */
        .st-emotion-cache-1y4p8pa input,
        .st-emotion-cache-1y4p8pa {
            color: #111111 !important;
            background-color: #ffffff !important;
            border: 1px solid #ddd !important;
        }
        
        /* Text area */
        .stTextArea textarea {
            color: #111111 !important;
            background-color: #ffffff !important;
            border: 1px solid #ddd !important;
        }
        
        /* Text input */
        .stTextInput input {
            color: #111111 !important;
            background-color: #ffffff !important;
            border: 1px solid #ddd !important;
        }
        
        /* Buttons */
        .stButton button {
            background-color: #FFD814 !important;
            color: #111111 !important;
            font-weight: 500 !important;
            border: none !important;
        }
        
        .stButton button:hover {
            background-color: #F7CA00 !important;
            color: #111111 !important;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] button {
            color: #111111 !important;
        }
        
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            color: #111111 !important;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
            color: #111111 !important;
            background-color: #f0f0f0 !important;
        }
        
        .streamlit-expanderContent {
            color: #111111 !important;
        }
        
        /* Alert/Success/Info/Warning messages */
        .stAlert {
            background-color: #e7f3ff !important;
        }
        
        .stAlert p, .stAlert div, .stAlert span {
            color: #111111 !important;
        }
        
        .stAlert[data-baseweb="notification"]:has(.stAlertIconSuccess) {
            background-color: #d4edda !important;
        }
        
        /* Metric cards */
        .stMetric label, .stMetric div {
            color: #111111 !important;
        }
        
        /* Download button */
        .stDownloadButton button {
            background-color: #FFD814 !important;
            color: #111111 !important;
        }
        
        /* Radio buttons */
        .stRadio label, .stRadio span {
            color: #111111 !important;
        }
        
        /* Checkbox */
        .stCheckbox label, .stCheckbox span {
            color: #111111 !important;
        }
        
        /* Audio player */
        .stAudio {
            color: #111111;
        }
        
        /* Code blocks */
        code, pre {
            color: #111111 !important;
            background-color: #f5f5f5 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 style="color: #232f3e; font-size: 2rem;">🌐 Voice Vision Translator</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color: #555555; margin-bottom: 20px;">Translate Text and Voice between multiple languages with ease</p>', unsafe_allow_html=True)

    # How to use section
    with st.expander("📌 How to Use This Translator", expanded=False):
        st.markdown("""
        **1. Text Translation:**
        - Select source and target languages from dropdowns
        - Type or paste your text in the text area
        - Click 'Translate Text' button
        
        **2. Voice Translation:**
        - Select your speaking language
        - Click the microphone button to record
        - Speak clearly into your microphone
        - Click stop when finished
        - Select target language and click 'Translate Voice Input'
        
        **3. History:**
        - View all your past translations
        - Play audio of translations
        - Clear history when needed
        """)

    # Initialize translator
    translator = Translator()

    # Language mapping
    lang_map = {
        "en": "English", "hi": "Hindi", "fr": "French", "de": "German",
        "es": "Spanish", "it": "Italian", "zh-cn": "Chinese (Simplified)", "ja": "Japanese",
        "ko": "Korean", "ar": "Arabic", "ru": "Russian", "te": "Telugu",
        "ta": "Tamil", "bn": "Bengali", "pa": "Punjabi", "gu": "Gujarati", "kn": "Kannada"
    }
    lang_codes = {v: k for k, v in lang_map.items()}

    # Session state
    if 'translation_history' not in st.session_state:
        st.session_state.translation_history = []
    if 'voice_text' not in st.session_state:
        st.session_state.voice_text = ""

    def add_to_history(source_text, source_lang, translated_text, target_lang):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.translation_history.append({
            "timestamp": timestamp,
            "source_language": source_lang,
            "source_text": source_text,
            "target_language": target_lang,
            "translated_text": translated_text
        })

    def get_text_download_link(text, filename="translation.txt"):
        b = BytesIO()
        b.write(text.encode())
        b.seek(0)
        return st.download_button("📥 Download Translation", b, file_name=filename)

    def play_audio(text, lang_code):
        try:
            if not text:
                return None
            tts = gTTS(text=text, lang=lang_code, slow=False)
            audio_path = os.path.join(tempfile.gettempdir(), f"voice_vision_audio_{hash(text)}_{lang_code}.mp3")
            tts.save(audio_path)
            with open(audio_path, "rb") as audio_file:
                audio_data = audio_file.read()
            os.unlink(audio_path)
            return audio_data
        except Exception as e:
            return None

    # Create tabs
    tab1, tab2, tab3 = st.tabs(["💬 Text Input", "🎤 Microphone Input", "📚 History"])

    with tab1:
        st.markdown("### Text Translation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Source Language**")
            source_lang = st.selectbox(
                "Select source language", 
                list(lang_map.values()), 
                index=0, 
                key="text_source_lang",
                label_visibility="collapsed"
            )
            input_text = st.text_area(
                "Enter text to translate", 
                height=150, 
                placeholder="Type or paste your text here...",
                key="input_text_area"
            )
        
        with col2:
            st.markdown("**Target Language**")
            target_lang = st.selectbox(
                "Select target language", 
                list(lang_map.values()), 
                index=1, 
                key="text_target_lang",
                label_visibility="collapsed"
            )
            
            translation_container = st.container()
            
            if st.button("🌐 Translate Text", key="text_translate", use_container_width=True) and input_text:
                try:
                    with st.spinner("Translating..."):
                        result = translator.translate(
                            input_text, 
                            src=lang_codes[source_lang], 
                            dest=lang_codes[target_lang]
                        )
                        translated_text = result.text
                        
                        with translation_container:
                            st.success("✅ Translation Complete!")
                            st.text_area("Translated Text", translated_text, height=150, key="text_translation_result")
                            
                            col_download, col_audio = st.columns(2)
                            with col_download:
                                get_text_download_link(translated_text, f"translation_{target_lang}.txt")
                            with col_audio:
                                audio_bytes = play_audio(translated_text, lang_codes[target_lang])
                                if audio_bytes:
                                    st.audio(audio_bytes, format="audio/mp3")
                        
                        add_to_history(input_text, source_lang, translated_text, target_lang)
                
                except Exception as e:
                    st.error(f"Translation Error: {e}")

    with tab2:
        st.markdown("### Voice Translation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Speaking Language**")
            mic_source_lang = st.selectbox(
                "Select your speaking language", 
                list(lang_map.values()), 
                index=0, 
                key="mic_source_lang",
                label_visibility="collapsed"
            )
            
            st.markdown("**Record your voice:**")
            st.caption("Click the microphone button below, speak clearly, then click stop")
            
            audio = mic_recorder(
                start_prompt="🎤 Start Recording",
                stop_prompt="⏹️ Stop Recording",
                just_once=True,
                use_container_width=True,
                format="wav",
                key="voice_recorder"
            )
            
            if audio:
                st.audio(audio['bytes'], format="audio/wav")
                st.success(f"✅ Recording saved! Duration: {audio.get('duration', 0):.1f} seconds")
                
                with st.spinner("Converting speech to text..."):
                    try:
                        import speech_recognition as sr
                        
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                            temp_path = temp_file.name
                            temp_file.write(audio['bytes'])
                        
                        recognizer = sr.Recognizer()
                        with sr.AudioFile(temp_path) as source:
                            recognizer.adjust_for_ambient_noise(source)
                            audio_data = recognizer.record(source)
                            
                            try:
                                voice_text = recognizer.recognize_google(
                                    audio_data, 
                                    language=lang_codes[mic_source_lang]
                                )
                                st.session_state.voice_text = voice_text
                                st.success(f"🎤 Recognized: {voice_text}")
                            except sr.UnknownValueError:
                                st.error("Could not understand the audio. Please speak clearly and try again.")
                            except sr.RequestError as e:
                                st.error(f"Speech recognition service error: {e}")
                        
                        os.unlink(temp_path)
                        
                    except Exception as e:
                        st.error(f"Error processing audio: {e}")
                        st.info("Make sure you have SpeechRecognition installed: pip install SpeechRecognition")
            
            if st.session_state.voice_text:
                st.markdown("**Transcribed Text:**")
                st.text_area("Recognized Speech", st.session_state.voice_text, height=80, key="transcribed_text", disabled=True)
        
        with col2:
            st.markdown("**Target Language**")
            mic_target_lang = st.selectbox(
                "Translate to", 
                list(lang_map.values()), 
                index=1, 
                key="mic_target_lang",
                label_visibility="collapsed"
            )
            
            voice_translation_container = st.container()
            
            translate_button = st.button("🌐 Translate Voice Input", key="translate_voice", use_container_width=True)
            
            if translate_button and st.session_state.voice_text:
                try:
                    with st.spinner("Translating..."):
                        result = translator.translate(
                            st.session_state.voice_text,
                            src=lang_codes[mic_source_lang],
                            dest=lang_codes[mic_target_lang],
                        )
                        voice_translated_text = result.text
                        
                        with voice_translation_container:
                            st.success("✅ Translation Complete!")
                            st.text_area("Translated Text", voice_translated_text, height=100, key="voice_translation_result")
                            
                            col_download, col_audio = st.columns(2)
                            with col_download:
                                get_text_download_link(voice_translated_text, f"voice_translation_{mic_target_lang}.txt")
                            with col_audio:
                                audio_bytes = play_audio(voice_translated_text, lang_codes[mic_target_lang])
                                if audio_bytes:
                                    st.audio(audio_bytes, format="audio/mp3")
                        
                        add_to_history(st.session_state.voice_text, mic_source_lang, voice_translated_text, mic_target_lang)
                        
                except Exception as e:
                    st.error(f"Translation Error: {e}")
            
            elif translate_button and not st.session_state.voice_text:
                st.warning("Please record and transcribe audio first using the microphone button above.")

    with tab3:
        st.markdown("### Translation History")
        
        if len(st.session_state.translation_history) > 0:
            for i, entry in enumerate(reversed(st.session_state.translation_history)):
                timestamp = entry.get("timestamp", "Unknown time")
                with st.expander(f"{entry['source_language']} → {entry['target_language']} ({timestamp})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Source ({entry['source_language']}):**")
                        st.text_area(f"Source Text {i}", entry['source_text'], height=80, key=f"src_{i}")
                    
                    with col2:
                        st.markdown(f"**Translation ({entry['target_language']}):**")
                        st.text_area(f"Translated Text {i}", entry['translated_text'], height=80, key=f"trs_{i}")
                    
                    audio_bytes = play_audio(entry['translated_text'], lang_codes[entry['target_language']])
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
            
            if st.button("🗑️ Clear History", use_container_width=True):
                st.session_state.translation_history = []
                st.session_state.voice_text = ""
                st.rerun()
        else:
            st.info("No translation history yet. Start translating to build your history!")

if __name__ == "__main__":
    main()