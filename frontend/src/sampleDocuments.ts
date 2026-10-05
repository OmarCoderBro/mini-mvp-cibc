// Synthetic demo documents shown in the UI. These mirror the plain-text
// files in backend/sample_documents/ so the reviewer can see and edit the
// exact text that will be sent to the backend. All content is fictional.

export interface SampleDocument {
  id: string;
  label: string;
  documentName: string;
  text: string;
}

export const SAMPLE_DOCUMENTS: SampleDocument[] = [
  {
    id: "clean",
    label: "Clean registration (expected: Ready for reviewer)",
    documentName: "clean_registration.txt",
    text: `CERTIFICATE OF BUSINESS REGISTRATION
(SYNTHETIC DEMO DOCUMENT — NOT A REAL FILING)

This certifies that the business named below has been registered under
fictional Demo Province business registry rules for the purposes of this
software demonstration only.

Legal Business Name: Acme Widgets Holdings Ltd.
Registration Number: BC-1029384
Registered Address: 100 Fictional Way, Toronto, ON, M4B 1B3
Issue Date: 2024-01-15
Expiration Date: 2027-01-15

This document contains no real business, government, or personal
information and must not be treated as evidence of any actual legal
entity.
`,
  },
  {
    id: "expired",
    label: "Expired registration (expected: Needs attention)",
    documentName: "expired_registration.txt",
    text: `CERTIFICATE OF BUSINESS REGISTRATION
(SYNTHETIC DEMO DOCUMENT — NOT A REAL FILING)

This certifies that the business named below has been registered under
fictional Demo Province business registry rules for the purposes of this
software demonstration only.

Legal Business Name: Northwind Traders Co.
Registration Number: ON-5544332
Registered Address: 45 Imaginary Street, Ottawa, ON, K1A 0B1
Issue Date: 2019-04-02
Expiration Date: 2024-04-02

This document contains no real business, government, or personal
information and must not be treated as evidence of any actual legal
entity.
`,
  },
  {
    id: "missing-fields",
    label: "Missing fields registration (expected: Needs attention)",
    documentName: "missing_fields_registration.txt",
    text: `CERTIFICATE OF BUSINESS REGISTRATION
(SYNTHETIC DEMO DOCUMENT — NOT A REAL FILING)

This certifies that the business named below has been registered under
fictional Demo Province business registry rules for the purposes of this
software demonstration only.

Legal Business Name: Fictional Harbor Imports Inc.
Registration Number: [NOT PROVIDED]
Registered Address: 7 Pretend Avenue, Vancouver, BC
Issue Date: 2023-06-01
Expiration Date:

This document contains no real business, government, or personal
information and must not be treated as evidence of any actual legal
entity.
`,
  },
];
