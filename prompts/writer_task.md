Generate product descriptions for the following product:

## Product Details
- **Product Name:** {product_name}
- **Category:** {category}
- **Brand:** {brand}
- **Color:** {color}
- **Size:** {size}
- **Packaging:** {packaging}
- **Certifications:** {certifications}
- **Tax/Afgift:** {afgift}

## Supplier Information
{supplier_info}

## Product URL
{product_url}

## Required Output Fields
1. **DESC_SHORT**: A short 2–5 word descriptive fragment (not a sentence) capturing the product’s core function or feature.

2. **DESC_LONG**:
   - **Structure**:
     - 1–2 paragraphs explaining purpose, benefits, and typical applications.
     - Optional paragraph covering certifications or sustainable materials (only if relevant).
     - Separate paragraph for the afgift notice if triggered.
     - End with a structured specification list in this exact order:
       - Farve: {color}
       - Størrelse: {size}
       - Brand: {brand}
       - Certificeringer: {certifications}
       - Forpakning: {packaging}
   - **Sustainability Rules**:
     Mention sustainability ONLY if supported by:
     - Recognized certifications (e.g., FSC, EU Økologisk, Svanemærket), OR
     - Clearly sustainable materials (e.g., bagasse, RPET, PLA, recycled plastic).
     Never:
     - Invent sustainability benefits
     - Use vague claims like “bæredygtig”, “miljøvenlig”, “grøn” unless justified
     - Imply environmental advantages not grounded in data
   - **Afgift Logic**:
     If “Tax/Afgift” is a numeric value > 0:
       Add this paragraph on its own line:
       "OBS: Prisen er eksklusiv emballageafgift. Se den samlede pris i kurven."
     If the value is 0, not numeric, or unknown:
       Do NOT include afgift text.

3. **PROD_SEARCHWORD**: Provide 5–10 relevant generic search keywords. Do NOT include:
   - The product name
   - The brand name
   - Uncommon adjectives or filler words

4. **META_DESCRIPTION**:
   - Max 155 characters
   - Must be factual and avoid claims not supported by product data
   - End with: “Køb her »”

## Output Rules
- Return ONLY a valid JSON object.
- No additional commentary, markdown, text, or explanations.
