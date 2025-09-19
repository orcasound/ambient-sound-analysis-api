import { MasterPlaylist, MediaPlaylist, PostProcess } from './types';
declare function stringify(playlist: MasterPlaylist | MediaPlaylist, postProcess?: PostProcess): string;
export default stringify;
