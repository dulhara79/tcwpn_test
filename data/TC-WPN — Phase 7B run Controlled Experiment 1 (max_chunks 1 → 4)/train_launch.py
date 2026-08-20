import os, sys, torch
sys.path.insert(0, '/kaggle/working/tcwpn_test/src')
sys.path.insert(0, '/kaggle/working/tcwpn_test')
if os.environ.get('TCWPN_GRAD_CHECKPOINT') == '1':
    import tcwpn.model as TM
    _orig = TM.build_model
    def build_model(cfg):
        m = _orig(cfg)
        try:
            m.embedder.bert.gradient_checkpointing_enable(
                gradient_checkpointing_kwargs={'use_reentrant': False})
            print('[launcher] gradient checkpointing ENABLED')
        except Exception as e:
            print('[launcher] could not enable checkpointing:', e)
        return m
    TM.build_model = build_model
import runpy
sys.argv = ['scripts.train'] + sys.argv[1:]
runpy.run_module('scripts.train', run_name='__main__')
