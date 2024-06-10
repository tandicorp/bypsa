# -*- encoding: utf-8 -*-
import unicodedata


def elimina_tildes(s):
    '''
    Metodo para eliminar tildes y caracteres especiales no permitidos en la mayoria de formatos de bancos
    '''
    s = s.upper()
    s = s.replace(u'Ñ', 'N')
    s = s.replace(u'-', '')
    s = s.replace(u'_', '')
    s = s.replace(u',', '')
    s = s.replace(u'.', '')
    s = s.replace(u'!', '')
    s = s.replace(u'#', '')
    s = s.replace(u'(', '')
    s = s.replace(u')', '')
    s = s.replace(u'{', '')
    s = s.replace(u'}', '')
    s = s.replace(u'[', '')
    s = s.replace(u']', '')
    s = ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))
    return s