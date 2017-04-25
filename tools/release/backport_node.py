#!/usr/bin/env python
# Copyright 2017 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Use this script to cherry-pick a V8 commit to backport to a Node.js checkout.

Requirements:
  - Node.js checkout to backport to.
  - V8 checkout that contains the commit to cherry-pick.

Usage:
  $ backport_node.py <path_to_v8> <path_to_node> <commit-hash>

  This will apply the commit to <path_to_node>/deps/v8 and create a commit in
  the Node.js checkout and copy over the original commit message.

Optional flags:
  --no-review  Run `gclient sync` on the V8 checkout before updating.
"""

import argparse
import os
import subprocess
import sys

TARGET_SUBDIR = os.path.join("deps", "v8")

def CherryPick(options):
  print ">> Apply patch."
  patch = subprocess.Popen(["git", "diff-tree", "-p", options.commit],
                           stdout=subprocess.PIPE, cwd=options.v8_path)
  patch.wait()
  try:
    subprocess.check_output(["git", "apply", "-3", "--directory=%s" % TARGET_SUBDIR],
                            stdin=patch.stdout, cwd=options.node_path)
  except:
    print ">> In another shell, please resolve patch conflicts"
    print ">> and `git add` affected files."
    print ">> Finally continue by entering RESOLVED."
    while raw_input("[RESOLVED]") != "RESOLVED":
      print ">> You need to type RESOLVED"

def CreateCommit(options):
  print ">> Creating commit."
  # Find short hash from source.
  shorthash = subprocess.check_output(
      ["git", "rev-parse", "--short", options.commit],
      cwd=options.v8_path).strip()

  # Commit message
  title = "deps: backport %s from upstream V8"  % shorthash
  body = subprocess.check_output(
      ["git", "log", options.commit, "-1", "--format=%B"],
      cwd=options.v8_path).strip()
  body = '\n'.join("    " + line for line in body.splitlines())

  message = title + "\n\nOriginal commit message:\n\n" + body

  # Create commit at target.
  review_message = "" if options.no_review else "-e"
  git_commands = [
    ["git", "checkout", "-b", "backport_%s" % shorthash],  # new branch
    ["git", "add", TARGET_SUBDIR],                         # add files
    ["git", "commit", "-m", message, review_message]       # new commit
  ]
  for command in git_commands:
    subprocess.check_call(command, cwd=options.node_path)

def ParseOptions(args):
  parser = argparse.ArgumentParser(description="Backport V8 commit to Node.js")
  parser.add_argument("v8_path", help="Path to V8 checkout")
  parser.add_argument("node_path", help="Path to Node.js checkout")
  parser.add_argument("commit", help="Commit to backport")
  parser.add_argument("--no-review", action="store_true",
                      help="Skip editing commit message")
  options = parser.parse_args(args)
  options.v8_path = os.path.abspath(options.v8_path)
  assert os.path.isdir(options.v8_path)
  options.node_path = os.path.abspath(options.node_path)
  assert os.path.isdir(options.node_path)
  return options

def Main(args):
  options = ParseOptions(args)
  try:
    CherryPick(options)
    CreateCommit(options)
  except:
    print ">> Failed. Resetting."
    subprocess.check_output(["git", "reset", "--hard"], cwd=options.node_path)
    raise

if __name__ == "__main__":
  Main(sys.argv[1:])
