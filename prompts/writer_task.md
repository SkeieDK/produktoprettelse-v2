Generate a structured JSON product description with HTML formatting.

## Product Data
- **Name:** {product_name}
- **Category:** {category}
- **Brand:** {brand}
- **Color:** {color}
- **Size:** {size}
- **Packaging:** {packaging}
- **Certifications:** {certifications}
- **Afgift (packaging fee):** {afgift} DKK

## Supplier Information
{supplier_info}

## OUTPUT FORMAT (valid JSON only)
{{
  "DESC_SHORT": "Concise one-liner description, max 100 chars, NO HTML",
  "DESC_LONG": "Rich HTML-formatted description with <strong>labels:</strong> value format. Use <br /><br /> between sections. Include materials, dimensions, certifications, usage, storage info.",
  "PROD_SEARCHWORD": "keyword1, keyword2, keyword3, keyword4, keyword5",
  "META_DESCRIPTION": "SEO description under 160 chars, NO HTML, must end with Køb her »"
}}

## IMPORTANT RULES FOR DESC_LONG
1. Start with primary use case
2. Use plain text `Field Name: value` format for regular specifications (e.g., `Materiale: PP`)
3. Use `<strong>` ONLY for special sections: `<strong>OBS:</strong>` and section headers like `<strong>Øvrig information</strong>`
4. Separate sections with `<br /><br />`
5. Include all available: material, dimensions, temperature range, approvals, packaging details
6. Group related specs together (e.g., dimensions: height, diameter, volume)
7. Add usage scenarios and benefits at the end
8. **Never use newlines - only `<br />` and `<br /><br />`**
9. If afgift > 0, include: `<strong>OBS:</strong> Prisen er eksklusiv emballageafgift. Se den samlede pris i kurven.<br /><br />`

## EXAMPLE OUTPUT
{{
  "DESC_SHORT": "Hvide drikkebæger til take-away og venteværelser",
  "DESC_LONG": "Klassiske hvide drikkebæger af plast til brug i venteværelse, eller når rent service er udenfor rækkevidde. Hver kasse indeholder 3000 drikkebæger fordelt i 30 poser.<br /><br /><strong>OBS:</strong> Prisen er eksklusiv emballageafgift. Se den samlede pris i kurven.<br /><br />Materiale: PP - Polypropylen<br />Højde: 9,8 cm<br />Diameter: 7 cm<br />Volumen: 21 cl<br />Godkendelse: -40 °C til +100 °C<br />Forpakning: 30 ps x 100 stk.<br /><br /><strong>Øvrig information (kun til storkøb)</strong><br />Antal salgsenheder på palle: 18 ks.",
  "PROD_SEARCHWORD": "drikkebæger, plastbæger, hvide bæger, engangsbæger, take-away bæger",
  "META_DESCRIPTION": "Hvide drikkebæger til B2B. 3000 stk per kasse, temperaturtest godkendt. Køb her »"
}}

## Sustainability Rules
- Mention ONLY if supported by certifications (FSC, Svanemærket) or materials (RPET, PLA, bagasse).
- Do not invent claims or use vague terms.

## Validation
- Output must be valid JSON.
- No markdown, no extra text.
- DESC_LONG **MUST** contain `<br />` tags
