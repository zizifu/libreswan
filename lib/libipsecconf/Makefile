# Libreswan library for parsing configuration files
#
# Copyright (C) 2005 Michael Richardson <mcr@xelerance.com> Xelerance Corporation
# Copyright (C) 2012 Paul Wouters <paul@libreswan.org>
# Copyright (C) 2015 Andrew Cagney <cagney@gnu.org>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See <http://www.fsf.org/copyleft/gpl.txt>.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

LIBRARY=ipsecconf
LIB=lib${LIBRARY}.a
MANDIR=$(MANTREE)/man3

ONEFILE=parser.y
SRCS=confread.c confwrite.c starterwhack.c starterlog.c
SRCS+=parser.tab.c lex.yy.c keywords.c oeconns.c
SRCS+=interfaces.c

#enable to get lots more debugging about semantics.
#CFLAGS+=-DPARSER_TYPE_DEBUG

OBJS=${SRCS:.c=.o}

ifdef top_srcdir
include ${top_srcdir}/mk/library.mk
else
include ../../mk/library.mk
endif

# Hack to force the generated files to be built first.  Not too bad
# since all the $(OBJS) indirectly depend on the header anyway.
$(OBJS): parser.tab.h

# Use UNIX basename to strip off the directory.
# Use sed to work around two bugs:
#
# - flex < 2.5.35 generates an extern that isn't good
#
# - flex on RHEL 7 generates code that provokes GCC to warn
#   about comparing a signed value with an unsigned value
#   (Combination of a new GCC and an old flex).
#   Adding one cast makes RHEL 6's GCC unhappy, so we add two.
#   On RHEL 6, i is int and _yybytes_len is int.
#   On RHEL 7, i is int and _yybytes_len is yy_size_t
#   On Fedora 21, i is yy_size_t and _yybytes_len is yy_size_t
#   On some architectures, yy_size_t is wider than int;
#   which makes a mixed comparison OK.
#
# Avoid sed -i which somehow causes unwritable files
# on fedora 20 with 9p filesystem mount.
# Avoid creating the target file until it is done.
lex.yy.c: parser.l
	cd $(builddir) && \
	$(LEX) -o $@.$$$$ $(srcdir)/$$(basename $<) && \
	sed -e 's/for ( i = 0; i < _yybytes_len; ++i )$$/for ( i = 0; (yy_size_t)i < (yy_size_t)_yybytes_len; ++i )/' \
	    -e '/^extern int isatty.*$$/d' $@.$$$$ >SEDTMP$$$$ && \
	rm $@.$$$$ && \
	mv SEDTMP$$$$ $@

# Use wild card rule so that GNU Make knows that both are output from
# a single recipe.
# - sed command for workaround for older bison vs GCC warning
# - avoid sed -i which somehow causes unwritable files
#   on fedora 20 with 9p filesystem mount
# - avoid creating the target file until it is done
%.tab.h %.tab.c: %.y
	cd $(builddir) && \
	$(BISON) ${BISONOSFLAGS} -v --defines=$$(basename $< .y).tab.h -o $$(basename $< .y).tab.c$$$$ $(srcdir)/$$(basename $<) && \
	sed -e '/^ *#/s/if YYENABLE_NLS/if defined(YYENABLE_NLS) \&\& YYENABLE_NLS/' \
		-e '/^ *#/s/if YYLTYPE_IS_TRIVIAL/if defined(YYLTYPE_IS_TRIVIAL) \&\& YYLTYPE_IS_TRIVIAL/' \
		$$(basename $< .y).tab.c$$$$ >SEDTMP$$$$ && \
	rm $$(basename $< .y).tab.c$$$$ && \
	mv SEDTMP$$$$ $$(basename $< .y).tab.c

clean: parser-clean
.PHONY: parser-clean
parser-clean:
	cd $(builddir) && $(RM) -f SEDTMP* *.tab.[cdho] *.dot *.output lex.yy.[cdho]
