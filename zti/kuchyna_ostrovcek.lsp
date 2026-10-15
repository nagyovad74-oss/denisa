;;; ===========================================================================
;;; KUCHYNSKY OSTROVCEK SO STOLICKAMI
;;; Vygenerovane skriptom zti/kuchyna_ostrovcek.py - needitovat rucne.
;;;
;;; Pouzitie v AutoCADe (vykres v mm):
;;;   1. APPLOAD -> nacitat tento subor
;;;   2. prikaz OSTROVCEK
;;;      - vyber stol (a stare stolicky) na odstranenie, Enter
;;;      - klikni stred ostrovceka
;;;      - zadaj natocenie dlhsej strany (stolicky su na strane "vpravo" od smeru natocenia)
;;;   Vsetko sa vrati jednym Ctrl+Z. Vykres sa neuklada.
;;;   Z MCP servera / run_lisp:  (ostr:kresli x y uhol_v_stupnoch)
;;; ===========================================================================

(defun ostr:p (x y)
  (list (+ ostr:ox (- (* x (cos ostr:a)) (* y (sin ostr:a))))
        (+ ostr:oy (+ (* x (sin ostr:a)) (* y (cos ostr:a))))
        0.0))
(defun ostr:em (lst) (if (not (entmake lst)) (setq ostr:err (1+ ostr:err))))
(defun ostr:pl (lay pts cl)
  (ostr:em
    (append
      (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") (cons 8 lay)
            '(100 . "AcDbPolyline") (cons 90 (length pts)) (cons 70 cl))
      (mapcar '(lambda (v) (cons 10 (reverse (cdr (reverse (ostr:p (car v) (cadr v))))))) pts))))
(defun ostr:layer (name col lw desc)
  (if (not (tblsearch "LAYER" name)) (command "_.-LAYER" "_N" name ""))
  (command "_.-LAYER" "_C" (itoa col) name "_LW" lw name ""))

(defun ostr:geometria ()
  (ostr:pl "INT_NABYTOK" (list '(-900.0 -450.0) '(900.0 -450.0) '(900.0 450.0) '(-900.0 450.0)) 1)
  (ostr:pl "INT_NABYTOK_SKRYTE" (list '(-900.0 -150.0) '(900.0 -150.0)) 0)
  (ostr:em (list '(0 . "CIRCLE") (cons 8 "INT_NABYTOK") (cons 10 (ostr:p -600.0 -580.0)) (cons 40 200.0)))
  (ostr:em (list '(0 . "CIRCLE") (cons 8 "INT_NABYTOK") (cons 10 (ostr:p -600.0 -580.0)) (cons 40 140.0)))
  (ostr:em (list '(0 . "CIRCLE") (cons 8 "INT_NABYTOK") (cons 10 (ostr:p 0.0 -580.0)) (cons 40 200.0)))
  (ostr:em (list '(0 . "CIRCLE") (cons 8 "INT_NABYTOK") (cons 10 (ostr:p 0.0 -580.0)) (cons 40 140.0)))
  (ostr:em (list '(0 . "CIRCLE") (cons 8 "INT_NABYTOK") (cons 10 (ostr:p 600.0 -580.0)) (cons 40 200.0)))
  (ostr:em (list '(0 . "CIRCLE") (cons 8 "INT_NABYTOK") (cons 10 (ostr:p 600.0 -580.0)) (cons 40 140.0)))
  (ostr:pl "INT_NABYTOK_SKRYTE" (list '(-1900.0 -1450.0) '(1900.0 -1450.0) '(1900.0 1450.0) '(-1900.0 1450.0)) 1)
  (ostr:em (list '(0 . "TEXT") (cons 8 "TEXT") (cons 10 (ostr:p -840.0 180.0)) (cons 40 90.0) (cons 1 "KUCHYNSK\\U+00DD OSTROV\\U+010CEK 1800\\U+00D7900") (cons 50 ostr:a)))
  (ostr:em (list '(0 . "TEXT") (cons 8 "TEXT") (cons 10 (ostr:p -840.0 50.0)) (cons 40 60.0) (cons 1 "skrinky 600, presah dosky 300, h = 900") (cons 50 ostr:a)))
  (ostr:em (list '(0 . "TEXT") (cons 8 "TEXT") (cons 10 (ostr:p -840.0 -60.0)) (cons 40 60.0) (cons 1 "3\\U+00D7 barov\\U+00E1 stoli\\U+010Dka \\U+00D8400") (cons 50 ostr:a)))
  (ostr:em (list '(0 . "TEXT") (cons 8 "TEXT") (cons 10 (ostr:p -1860.0 1350.0)) (cons 40 60.0) (cons 1 "min. vo\\U+013En\\U+00FD priestor 1000") (cons 50 ostr:a)))
)

(defun ostr:kresli (x y uhol / old)
  (setq ostr:ox x ostr:oy y ostr:a (* pi (/ uhol 180.0)) ostr:err 0)
  (setq old (mapcar (quote getvar) (quote ("CMDECHO" "CLAYER"))))
  (setvar "CMDECHO" 0)
  (command "_.UNDO" "_BE")
  (ostr:layer "INT_NABYTOK" 8 "0.25" "Nabytok - kuchynsky ostrovcek")
  (ostr:layer "INT_NABYTOK_SKRYTE" 9 "0.13" "Nabytok - skryte hrany, volny priestor")
  (ostr:layer "TEXT" 7 "0.25" "Texty a popisy")
  (ostr:geometria)
  (setvar "CLAYER" (nth 1 old))
  (command "_.UNDO" "_E")
  (setvar "CMDECHO" (nth 0 old))
  (princ (strcat "\nOstrovcek nakresleny. Neuspesnych entmake: " (itoa ostr:err)))
  ostr:err)

(defun c:OSTROVCEK (/ ss p a)
  (command "_.UNDO" "_BE")
  (princ "\nVyber stol (a stare stolicky) na odstranenie <Enter = nic>: ")
  (if (setq ss (ssget))
    (progn (command "_.ERASE" ss "")
           (princ (strcat "\nOdstranenych objektov: " (itoa (sslength ss))))))
  (setq p (getpoint "\nStred kuchynskeho ostrovceka: "))
  (if p
    (progn
      (setq a (getangle p "\nNatocenie dlhsej strany <0>: "))
      (ostr:kresli (car p) (cadr p) (if a (* 180.0 (/ a pi)) 0.0))))
  (command "_.UNDO" "_E")
  (princ))

(princ "\nOstrovcek nacitany. Spusti prikazom OSTROVCEK.")
(princ)
