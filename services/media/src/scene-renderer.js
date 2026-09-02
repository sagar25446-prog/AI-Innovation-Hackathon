import { SceneRenderer } from './interfaces.js';

/**
 * Default Scene Renderer
 * @implements {SceneRenderer}
 */
export class DefaultSceneRenderer extends SceneRenderer {
  /**
   * Render a scene
   * @param {Object} scene - Scene object from contract schema
   * @param {Object} providers - Providers to use
   * @param {import('./interfaces.js').TTSProvider} providers.ttsProvider - TTS provider
   * @param {import('./interfaces.js').AvatarProvider} providers.avatarProvider - Avatar provider
   * @returns {Promise<import('./interfaces.js').MediaResult>}
   */
  async renderScene(scene, providers) {
    const { ttsProvider, avatarProvider } = providers;
    let audioResult = null;
    let avatarResult = null;
    let durationSeconds = scene.durationSeconds || 5;
    let captions = [];
    
    // Contract schema defines narration as a plain string
    const narrationText = typeof scene.narration === 'string' 
      ? scene.narration 
      : (scene.narration?.text || '');
    const language = scene.language || providers.language || 'english';

    // Try TTS
    try {
      if (narrationText) {
        audioResult = await ttsProvider.synthesize(narrationText, language);
        durationSeconds = audioResult.durationSeconds || durationSeconds;
      }
    } catch (e) {
      console.warn("TTS generation failed, using text-only captions:", e);
    }

    // Try Avatar
    try {
      if (narrationText) {
        avatarResult = await avatarProvider.generateAvatar(
          narrationText,
          audioResult ? audioResult.audioUrl : '',
          { durationSeconds }
        );
      }
    } catch (e) {
      console.warn("Avatar generation failed, using static placeholder:", e);
    }

    // Generate captions from narration text
    if (narrationText) {
      // Split by sentence roughly
      const segments = narrationText.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 0);
      if (segments.length > 0) {
        let currentTime = 0;
        const timePerSegment = durationSeconds / segments.length;
        
        captions = segments.map((seg) => {
          const c = {
            text: seg.trim(),
            startTime: currentTime,
            endTime: currentTime + timePerSegment,
            language
          };
          currentTime += timePerSegment;
          return c;
        });
      }
    }

    // Prepare Visual Canvas
    const visual = scene.visual || { type: 'unknown', data: {} };
    let renderHint = 'standard';
    
    // Map of known visual types
    const knownTypes = ['circuit', 'equation', 'graph', 'concept_map'];
    let visualType = knownTypes.includes(visual.type) ? visual.type : 'concept_card';

    return {
      teacherPanel: avatarResult ? {
        type: 'video',
        url: avatarResult.videoUrl,
        thumbnailUrl: avatarResult.thumbnailUrl
      } : {
        type: 'image',
        url: 'mock://placeholder/teacher.jpg',
        thumbnailUrl: 'mock://placeholder/teacher_thumb.jpg'
      },
      visualCanvas: {
        type: visualType,
        data: visual.data || {},
        renderHint
      },
      captions,
      durationSeconds,
      status: 'success'
    };
  }
}
