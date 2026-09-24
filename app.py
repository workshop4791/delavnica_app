
# --- AI Funkcija za prepoznavo skice z OpenAI (GPT-4o) ---
def ai_analiza_skice_z_gpt(slika_pil, api_key):
    try:
        client = OpenAI(api_key=api_key)
        
        # Pretvorba PIL slike v base64 za OpenAI API
        import base64
        buffered = io.BytesIO()
        slika_pil.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        prompt = (
            "Analiziraj to ročno narisano skico za laserski izrez plosce. "
            "Preberi vse dimenzije, napise in narisane luknje. "
            "Vrni IZKLJUČNO veljaven JSON v naslednjem formatu (brez dodatnega besedila ali markdowna, samo čisti JSON):\n"
            "{\n"
            '  "sirina_mm": 1500,\n'
            '  "visina_mm": 1000,\n'
            '  "luknje": [\n'
            "    {\n"
            '      "tip": "Okrogla",\n'
            '      "premer_mm": 20,\n'
            '      "x_mm": 150,\n'
            '      "y_mm": 850\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Vse dimenzije pretvori v milimetre (mm). Če so v metrih (m), pomnoži s 1000. "
            "Uporabljaj samo angleške ključe v JSON in brez šumnikov v vrednostih."
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_str}"},
                        },
                    ],
                }
            ],
            max_tokens=1000,
        )

        content = response.choices[0].message.content
        # Poskrbimo za pravilno dekodiranje UTF-8 znakov
        if isinstance(content, bytes):
            content = content.decode('utf-8')
            
        clean_json = content.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"Napaka pri AI analizi skice s GPT-4o: {e}")
        return None
