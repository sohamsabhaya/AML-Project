// Shared constants for the analysis flow: class names, labels, copy and thresholds.

export const DISCLAIMER =
  'AI-generated prediction for educational and research use only. It is not a medical diagnosis and must not replace review by a qualified clinician.'

export const CLASS_ORDER = ['glioma', 'meningioma', 'notumor', 'pituitary']

export const CLASS_LABELS = {
  glioma: 'Glioma',
  meningioma: 'Meningioma',
  notumor: 'No Tumor',
  pituitary: 'Pituitary Tumor',
}

// Soft badge colours per class: [background, text, bar colour].
export const CLASS_TONES = {
  glioma: ['#FEE2E2', '#991B1B', '#DC2626'],
  meningioma: ['#FEF3C7', '#92400E', '#D97706'],
  notumor: ['#DCFCE7', '#166534', '#16A34A'],
  pituitary: ['#EDE9FE', '#5B21B6', '#7C3AED'],
}

export const CLASS_EXPLANATIONS = {
  glioma:
    'The model found this image closest to examples it learned to label as glioma, a group of tumors that start in glial cells. This is a pattern match on the image, not a clinical finding.',
  meningioma:
    'The model found this image closest to examples it learned to label as meningioma, a type of tumor that grows from the membranes around the brain. This is a pattern match on the image, not a clinical finding.',
  notumor:
    'The model found this image closest to examples it learned to label as showing no tumor. A "No Tumor" output is not a guarantee that nothing is present and should not be read as reassurance.',
  pituitary:
    'The model found this image closest to examples it learned to label as pituitary tumor, which involves the pituitary gland at the base of the brain. This is a pattern match on the image, not a clinical finding.',
}

export const MODEL_OPTIONS = [
  { value: 'resnet50', label: 'ResNet50', hint: 'Transfer-learning model (default)' },
  { value: 'custom_cnn', label: 'Custom CNN', hint: 'Smaller model trained from scratch' },
  { value: 'both', label: 'Compare both', hint: 'Run both models and show where they agree' },
]

export const LIMITATIONS = [
  'Confidence is the model\'s score for its own output. It is not clinical certainty.',
  'The Grad-CAM heatmap is an explanatory visualization of where the model looked. It does not outline a tumor.',
  'The model was trained on a limited public dataset and may perform differently on other scanners or protocols.',
  'Only a single 2D image is analysed. No patient history or other scans are considered.',
]

export const LOW_CONFIDENCE = 0.6
export const PAGE_SIZE = 10
export const MAX_FILE_BYTES = 10 * 1024 * 1024

export const MAX_ENTROPY = Math.log(4)
