module Main where

import System.Environment
import Control.Monad
import qualified Data.Binary as Binary
import qualified Data.ByteString.Lazy.Char8 as BS
import qualified Data.Map as Map
import qualified Elm.Compiler.Type as Type
import qualified Elm.Compiler.Module as Module

main = do
	args <- getArgs
	let filename = head args
	let value = args !! 1
	binary <- BS.readFile filename
	let types = Module.interfaceTypes (Binary.decode binary)
	case Map.lookup value types of
		Just tipe -> putStrLn (Type.toString tipe)
		Nothing -> putStrLn "welp,"
	putStrLn "-------------------"
	mapM_ putStrLn $ Map.keys types

